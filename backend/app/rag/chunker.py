import re
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document

# Question type constants
QUESTION_TYPE_MCQ = "mcq"
QUESTION_TYPE_STRUCTURED_ESSAY = "structured_essay"
QUESTION_TYPE_ESSAY = "essay"


def extract_paper_year(text: str, file_path: Optional[str] = None) -> Optional[int]:
    """
    Automatically detects the exam paper year.
    1. Checks the filename/path first (e.g. 'data/past_papers/2015.pdf').
    2. Searches the document header text for exam codes or 4-digit years.
    """
    if file_path:
        path_match = re.search(r"(20\d{2})", file_path)
        if path_match:
            return int(path_match.group(1))

    header_sample = text[:2000]
    code_match = re.search(
        r"(?:OL\s*/\s*|G\.C\.E\..*?-?\s*|\b)(20\d{2})\b",
        header_sample,
        re.IGNORECASE
    )
    if code_match:
        return int(code_match.group(1))

    return None


def _is_instruction_continuation(line: str) -> bool:
    """Returns True if the line is part of standard exam instructions rather than a section heading."""
    instruction_continuations = re.compile(
        r"^Part\s*[AB][,\s]+(and|answer|together|in\s+the|selecting|of\s+the|questions\s+in)",
        re.IGNORECASE
    )
    return bool(instruction_continuations.match(line.strip()))


def split_questions(
    text: str,
    paper_year: Optional[int] = None,
    file_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Splits full PDF extracted text into structured question chunks using a
    sequential state-machine parser that cleanly separates Part I (MCQ 1-40),
    Part II Part A (Structured Essay 1-4), and Part II Part B (Essay 5-10).
    """
    if paper_year is None:
        paper_year = extract_paper_year(text, file_path)

    pages_text = re.split(r"(?:\n|^)---\s*Page\s+(\d+)\s*---", text, flags=re.IGNORECASE)

    page_blocks = []
    if len(pages_text) > 1:
        for i in range(1, len(pages_text), 2):
            p_num = int(pages_text[i])
            p_content = pages_text[i+1] if i + 1 < len(pages_text) else ""
            page_blocks.append((p_num, p_content))
    else:
        page_blocks.append((1, text))

    q_boundary_pattern = re.compile(
        r"(?:\n|^)\s*(?=(?:Question\s+)?([1-9]|[1-3][0-9]|40)\s*[\.\)]\s+)",
        re.IGNORECASE
    )

    part_a_header_pattern = re.compile(r"(?:^|\n)[ \t]*Part\s*[\-–]?\s*A\b", re.IGNORECASE)
    part_b_header_pattern = re.compile(r"(?:^|\n)[ \t]*Part\s*[\-–]?\s*B\b", re.IGNORECASE)

    _instruction_phrases = re.compile(
        r"answer\s+(four|three|two|one|all|only)\s+questions|in\s+the\s+space\s+provided"
        r"|tie\s+part\s+[ab]|hand\s+over|selecting\s+one|index\s+number|questions\s+no\.\s*5",
        re.IGNORECASE
    )

    raw_chunks = []
    current_section = QUESTION_TYPE_MCQ
    current_mcq_num = 0
    current_se_num = 0
    current_essay_num = 4

    for p_num, p_content in page_blocks:
        # Check if this page switches section via header lines
        if p_num >= 4:
            for m in part_a_header_pattern.finditer(p_content):
                start = m.start()
                content_start = start + (1 if p_content[start] == '\n' else 0)
                line_end = p_content.find('\n', content_start)
                line = p_content[content_start: line_end if line_end != -1 else content_start + 120]
                if not _is_instruction_continuation(line):
                    current_section = QUESTION_TYPE_STRUCTURED_ESSAY
                    break

            for m in part_b_header_pattern.finditer(p_content):
                start = m.start()
                content_start = start + (1 if p_content[start] == '\n' else 0)
                line_end = p_content.find('\n', content_start)
                line = p_content[content_start: line_end if line_end != -1 else content_start + 120]
                if not _is_instruction_continuation(line):
                    current_section = QUESTION_TYPE_ESSAY
                    break

        parts = q_boundary_pattern.split(p_content)
        preamble = parts[0].strip() if parts else ""

        # Check for Q1 in preamble when Part A starts
        preamble_q1_injected = False
        if current_section == QUESTION_TYPE_STRUCTURED_ESSAY and current_se_num == 0 and "Part A" in preamble:
            last_a_match = None
            for m in re.finditer(r"Part\s*[\-\u2013]?\s*A\b", preamble, re.IGNORECASE):
                last_a_match = m
            if last_a_match:
                q1_text = preamble[last_a_match.end():].strip()
                already_split = len(parts) > 1 and parts[1] == "1"
                is_instruction = bool(_instruction_phrases.search(q1_text[:200]))
                if q1_text and len(q1_text) > 20 and not is_instruction and not already_split:
                    diag_m = re.search(r"\[DIAGRAM:\s*(.*?)\]", q1_text, re.DOTALL)
                    q1_clean = re.sub(r"^(?:Question\s+)?1\s*[\.\)]\s*", "", q1_text, flags=re.IGNORECASE).strip()
                    full_q1_text = f"1. {q1_clean}" if q1_clean else f"1. {q1_text}"
                    current_se_num = 1
                    raw_chunks.append({
                        "question_number": 1,
                        "question_type": QUESTION_TYPE_STRUCTURED_ESSAY,
                        "page_number": p_num,
                        "has_diagram": bool(diag_m),
                        "diagram_description": diag_m.group(1).strip() if diag_m else None,
                        "stem": full_q1_text,
                        "options": {},
                        "full_text": full_q1_text,
                        "metadata": {
                            "question_number": 1,
                            "question_type": QUESTION_TYPE_STRUCTURED_ESSAY,
                            "page_number": p_num,
                            "has_diagram": bool(diag_m),
                            "paper_year": paper_year
                        }
                    })
                    preamble_q1_injected = True

        # Continuation of previous question
        if not preamble_q1_injected and preamble and raw_chunks:
            prev = raw_chunks[-1]
            if prev["question_type"] == QUESTION_TYPE_MCQ and current_section == QUESTION_TYPE_MCQ:
                prev["full_text"] += "\n" + preamble
                opt_m = re.findall(r"\(\s*([1-4])\s*\)\s*([^\(\n]+)", preamble)
                for o_num, o_val in opt_m:
                    if o_num not in prev["options"]:
                        prev["options"][o_num] = o_val.strip()
            elif prev["question_type"] == current_section:
                prev["full_text"] += "\n" + preamble

        if len(parts) <= 1:
            continue

        i = 1
        while i < len(parts):
            q_num_str = parts[i]
            q_body = parts[i+1] if i + 1 < len(parts) else ""
            i += 2

            if not q_num_str or not q_num_str.isdigit():
                continue

            q_number = int(q_num_str)
            body_clean = q_body.strip()

            # Section-specific sequential filtering
            if current_section == QUESTION_TYPE_MCQ:
                if q_number < 1 or q_number > 40:
                    if raw_chunks:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue

                is_instr = bool(_instruction_phrases.search(body_clean[:100]))
                has_words = bool(re.search(r"[a-zA-Z]{3,}", body_clean[:80]))

                if is_instr:
                    if raw_chunks:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue

                if q_number == current_mcq_num + 1 or (current_mcq_num == 0 and q_number == 1):
                    current_mcq_num = q_number
                    question_type = QUESTION_TYPE_MCQ
                elif q_number > current_mcq_num + 1:
                    has_options = bool(re.search(r"\(\s*[1-4]\s*\)", body_clean))
                    if q_number <= current_mcq_num + 2 and has_words and has_options:
                        current_mcq_num = q_number
                        question_type = QUESTION_TYPE_MCQ
                    else:
                        if raw_chunks:
                            raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                            for o_num, o_val in re.findall(r"\(\s*([1-4])\s*\)\s*([^\(\n]+)", body_clean):
                                if o_num not in raw_chunks[-1]["options"]:
                                    raw_chunks[-1]["options"][o_num] = o_val.strip()
                        continue
                elif q_number == current_mcq_num and has_words:
                    question_type = QUESTION_TYPE_MCQ
                else:
                    if raw_chunks:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue

            elif current_section == QUESTION_TYPE_STRUCTURED_ESSAY:
                # Valid questions in Part A are strictly 1, 2, 3, 4 sequentially
                if q_number == current_se_num + 1 and 1 <= q_number <= 4:
                    current_se_num = q_number
                    question_type = QUESTION_TYPE_STRUCTURED_ESSAY
                elif q_number == current_se_num and len(body_clean) > 20 and bool(re.search(r"[a-zA-Z]{3,}", body_clean[:60])):
                    question_type = QUESTION_TYPE_STRUCTURED_ESSAY
                else:
                    # Non-sequential or subpart number (e.g. 2. or 7. inside Q3/Q4) -> append to current chunk
                    if raw_chunks:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue

            else:  # current_section == QUESTION_TYPE_ESSAY
                # Valid questions in Part B are strictly 5, 6, 7, 8, 9, 10
                if q_number < 5 or q_number > 10:
                    if raw_chunks:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue

                if bool(_instruction_phrases.search(body_clean[:120])):
                    if raw_chunks:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue

                if q_number == current_essay_num + 1:
                    current_essay_num = q_number
                    question_type = QUESTION_TYPE_ESSAY
                elif q_number > current_essay_num and q_number <= current_essay_num + 2:
                    current_essay_num = q_number
                    question_type = QUESTION_TYPE_ESSAY
                elif q_number == current_essay_num:
                    question_type = QUESTION_TYPE_ESSAY
                else:
                    if raw_chunks:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue

            # Filter tiny spurious lines without letters
            if len(body_clean) < 10 and not re.search(r"\(\s*[1-4]\s*\)", body_clean) and not re.search(r"[a-zA-Z]", body_clean):
                continue

            # Ensure clean prefix
            body_without_prefix = re.sub(
                rf"^(?:Question\s+)?{q_number}\s*[\.\)]\s*",
                "",
                body_clean,
                flags=re.IGNORECASE
            ).strip()
            full_q_text = f"{q_number}. {body_without_prefix}" if body_without_prefix else f"{q_number}. {body_clean}"

            # Diagram detection
            diagram_match = re.search(r"\[DIAGRAM:\s*(.*?)\]", full_q_text, re.DOTALL)
            has_diagram = bool(diagram_match)
            diagram_description = diagram_match.group(1).strip() if diagram_match else None

            # MCQ option parsing
            options = {}
            if question_type == QUESTION_TYPE_MCQ:
                opt_matches = re.findall(r"\(\s*([1-4])\s*\)\s*([^\(\n]+)", full_q_text)
                for opt_num, opt_val in opt_matches:
                    opt_clean = opt_val.strip()
                    if opt_clean and opt_num not in options:
                        options[opt_num] = opt_clean

            # Stem text
            first_opt_match = re.search(r"\(\s*[1-4]\s*\)", full_q_text)
            if first_opt_match and question_type == QUESTION_TYPE_MCQ:
                stem_text = full_q_text[:first_opt_match.start()].strip()
            else:
                stem_text = full_q_text.strip()

            metadata = {
                "question_number": q_number,
                "question_type": question_type,
                "page_number": p_num,
                "has_diagram": has_diagram,
            }
            if paper_year:
                metadata["paper_year"] = paper_year
            if diagram_description:
                metadata["diagram_description"] = diagram_description

            raw_chunks.append({
                "question_number": q_number,
                "question_type": question_type,
                "page_number": p_num,
                "has_diagram": has_diagram,
                "diagram_description": diagram_description,
                "stem": stem_text,
                "options": options,
                "full_text": full_q_text,
                "metadata": metadata
            })

    # Post-process Part A: Check if Structured Essay Q4 is missing but embedded in Q3 text
    se_chunks = [c for c in raw_chunks if c["question_type"] == QUESTION_TYPE_STRUCTURED_ESSAY]
    se_nums = {c["question_number"] for c in se_chunks}
    if 1 in se_nums and 2 in se_nums and 3 in se_nums and 4 not in se_nums:
        q3_chunk = next(c for c in raw_chunks if c["question_type"] == QUESTION_TYPE_STRUCTURED_ESSAY and c["question_number"] == 3)
        q4_split = re.split(r"(?:\n|^)(?:15\s*\n+|(?:\(\s*v\s*\)[^\n]*\n+))(.*)", q3_chunk["full_text"], flags=re.DOTALL)
        if len(q4_split) > 1 and len(q4_split[1].strip()) > 80:
            q4_body = q4_split[1].strip()
            q3_chunk["full_text"] = q3_chunk["full_text"][:q3_chunk["full_text"].find(q4_body)].strip()
            q3_opt = re.search(r"\(\s*[1-4]\s*\)", q3_chunk["full_text"])
            q3_chunk["stem"] = q3_chunk["full_text"][:q3_opt.start()].strip() if q3_opt else q3_chunk["full_text"].strip()
            
            diag_m = re.search(r"\[DIAGRAM:\s*(.*?)\]", q4_body, re.DOTALL)
            q4_clean = re.sub(r"^(?:Question\s+)?4\s*[\.\)]\s*", "", q4_body, flags=re.IGNORECASE).strip()
            full_q4 = f"4. {q4_clean}" if q4_clean else f"4. {q4_body}"
            raw_chunks.append({
                "question_number": 4,
                "question_type": QUESTION_TYPE_STRUCTURED_ESSAY,
                "page_number": q3_chunk["page_number"],
                "has_diagram": bool(diag_m),
                "diagram_description": diag_m.group(1).strip() if diag_m else None,
                "stem": full_q4,
                "options": {},
                "full_text": full_q4,
                "metadata": {
                    "question_number": 4,
                    "question_type": QUESTION_TYPE_STRUCTURED_ESSAY,
                    "page_number": q3_chunk["page_number"],
                    "has_diagram": bool(diag_m),
                    "paper_year": paper_year
                }
            })

    # Merge duplicate question numbers within the same section
    cleaned_chunks = []
    seen_keys = set()
    for c in raw_chunks:
        key = (c["question_type"], c["question_number"])
        if key in seen_keys:
            for existing in cleaned_chunks:
                if (existing["question_type"] == c["question_type"] and 
                    existing["question_number"] == c["question_number"]):
                    has_letters_new = bool(re.search(r"[a-zA-Z]{4,}", c["stem"]))
                    has_letters_old = bool(re.search(r"[a-zA-Z]{4,}", existing["stem"]))
                    if has_letters_new and not has_letters_old:
                        existing["stem"] = c["stem"]
                        existing["full_text"] = c["full_text"] + "\n" + existing["full_text"]
                    else:
                        existing["full_text"] += "\n" + c["full_text"]
                    existing["options"].update(c["options"])
                    if c["has_diagram"]:
                        existing["has_diagram"] = True
                        existing["diagram_description"] = c["diagram_description"]
                        existing["metadata"]["has_diagram"] = True
                    break
        else:
            seen_keys.add(key)
            cleaned_chunks.append(c)

    # Sort chunks: MCQ (1..40), Structured Essay (1..4), Essay (5..10)
    type_order = {QUESTION_TYPE_MCQ: 1, QUESTION_TYPE_STRUCTURED_ESSAY: 2, QUESTION_TYPE_ESSAY: 3}
    cleaned_chunks.sort(key=lambda x: (type_order.get(x["question_type"], 99), x["question_number"]))

    return cleaned_chunks


def chunks_to_langchain_documents(chunks: List[Dict[str, Any]]) -> List[Document]:
    """
    Converts list of question chunk dicts into LangChain Document objects
    for vectorstore embedding.
    """
    documents = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk["full_text"],
            metadata=chunk["metadata"]
        )
        documents.append(doc)
    return documents