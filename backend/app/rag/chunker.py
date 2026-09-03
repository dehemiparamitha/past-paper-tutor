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


def _find_section_positions(text: str) -> Dict[str, Optional[int]]:
    """
    Finds the character positions of 'Part A' (Structured Essay) and 'Part B' (Essay)
    section headers in the full document text.
    Matches lines starting with 'Part A' (e.g. 'Part A Structured Essay Questions')
    and 'Part B' (e.g. 'Part B - Essay Questions').
    Ignores mentions inside instruction sentences like 'Answer four questions in Part A'.
    """
    part_a_pattern = re.compile(
        r"(?:^|\n)\s*Part\s*[\-–]?\s*A(?:\s*[\-–]?\s*(?:Structured|Essay)|\s*$|\s*\n)",
        re.IGNORECASE
    )
    part_b_pattern = re.compile(
        r"(?:^|\n)\s*Part\s*[\-–]?\s*B(?:\s*[\-–]?\s*Essay|\s*$|\s*\n)",
        re.IGNORECASE
    )

    m_a = part_a_pattern.search(text)
    m_b = part_b_pattern.search(text)

    return {
        "part_a_pos": m_a.start() if m_a else None,
        "part_b_pos": m_b.start() if m_b else None,
    }


def split_questions(
    text: str,
    paper_year: Optional[int] = None,
    file_path: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Splits full PDF extracted text into structured question chunks.

    Handles:
    - MCQ (Questions 1 to 40)
    - Structured Essay / Part A (Questions 1 to 4)
    - Essay / Part B (Questions 5 to 9)
    - Multi-page question continuations
    - Diagram descriptions [DIAGRAM: ...]
    - MCQ options (1) to (4)
    """
    # Auto-detect paper year
    if paper_year is None:
        paper_year = extract_paper_year(text, file_path)

    section_map = _find_section_positions(text)
    part_a_pos = section_map["part_a_pos"]
    part_b_pos = section_map["part_b_pos"]

    pages_text = re.split(r"(?:\n|^)---\s*Page\s+(\d+)\s*---", text, flags=re.IGNORECASE)

    raw_page_blocks = []
    if len(pages_text) > 1:
        if pages_text[0].strip():
            raw_page_blocks.append((1, pages_text[0], 0))
        offset = len(pages_text[0])
        for i in range(1, len(pages_text), 2):
            p_num = int(pages_text[i])
            p_content = pages_text[i+1] if i + 1 < len(pages_text) else ""
            raw_page_blocks.append((p_num, p_content, offset))
            offset += len(pages_text[i]) + len(p_content)
    else:
        raw_page_blocks.append((1, text, 0))

    # Regex matches question start numbers (1 to 40) strictly followed by dot or paren and space
    q_boundary_pattern = re.compile(
        r"(?:\n|^)\s*(?=(?:Question\s+)?([1-9]|[1-3][0-9]|40)\s*[\.\)]\s+)",
        re.IGNORECASE
    )

    raw_chunks = []
    current_mcq_num = 0

    for p_num, p_content, page_char_offset in raw_page_blocks:
        parts = q_boundary_pattern.split(p_content)
        preamble = parts[0].strip() if parts else ""

        # Check if preamble contains Part A header with Question 1 starting immediately
        if "Part A" in preamble and p_num >= 5:
            part_a_match = re.search(r"Part\s*[\-–]?\s*A.*?(?:\n|$)", preamble, re.IGNORECASE)
            if part_a_match:
                q1_text = preamble[part_a_match.end():].strip()
                if q1_text and len(q1_text) > 20:
                    diag_m = re.search(r"\[DIAGRAM:\s*(.*?)\]", q1_text, re.DOTALL)
                    raw_chunks.append({
                        "question_number": 1,
                        "question_type": QUESTION_TYPE_STRUCTURED_ESSAY,
                        "page_number": p_num,
                        "has_diagram": bool(diag_m),
                        "diagram_description": diag_m.group(1).strip() if diag_m else None,
                        "stem": q1_text,
                        "options": {},
                        "full_text": "1. " + q1_text,
                        "metadata": {
                            "question_number": 1,
                            "question_type": QUESTION_TYPE_STRUCTURED_ESSAY,
                            "page_number": p_num,
                            "has_diagram": bool(diag_m),
                            "paper_year": paper_year
                        }
                    })
        elif preamble and raw_chunks:
            # Preamble is a multi-page continuation of the previous question
            prev = raw_chunks[-1]
            if prev["question_type"] == QUESTION_TYPE_MCQ:
                prev["full_text"] += "\n" + preamble
                opt_m = re.findall(r"\(\s*([1-4])\s*\)\s*([^\(\n]+)", preamble)
                for o_num, o_val in opt_m:
                    if o_num not in prev["options"]:
                        prev["options"][o_num] = o_val.strip()
            else:
                prev["full_text"] += "\n" + preamble

        if len(parts) <= 1:
            continue

        content_offset = len(parts[0])

        i = 1
        while i < len(parts):
            q_num_str = parts[i]
            q_body = parts[i+1] if i + 1 < len(parts) else ""
            i += 2

            if not q_num_str or not q_num_str.isdigit():
                content_offset += len(q_num_str) + len(q_body)
                continue

            q_number = int(q_num_str)
            body_clean = q_body.strip()

            q_abs_pos = page_char_offset + content_offset
            content_offset += len(q_num_str) + len(q_body)

            # Assign section type
            if part_b_pos is not None and q_abs_pos >= part_b_pos:
                question_type = QUESTION_TYPE_ESSAY
            elif part_a_pos is not None and q_abs_pos >= part_a_pos:
                question_type = QUESTION_TYPE_STRUCTURED_ESSAY
            elif p_num >= 9:
                question_type = QUESTION_TYPE_ESSAY
            elif p_num >= 5:
                question_type = QUESTION_TYPE_STRUCTURED_ESSAY
            else:
                question_type = QUESTION_TYPE_MCQ

            # Section bounds validation
            if question_type == QUESTION_TYPE_MCQ:
                # Reject out-of-order jump numbers that are part of preamble/instructions (e.g. 22 appearing before 21)
                if current_mcq_num < 25 and q_number > current_mcq_num + 2:
                    if raw_chunks and raw_chunks[-1]["question_type"] == QUESTION_TYPE_MCQ:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue
                if current_mcq_num > 10 and q_number < current_mcq_num - 2:
                    if raw_chunks and raw_chunks[-1]["question_type"] == QUESTION_TYPE_MCQ:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue
                current_mcq_num = max(current_mcq_num, q_number)

            elif question_type == QUESTION_TYPE_STRUCTURED_ESSAY:
                if q_number > 4:
                    if raw_chunks and raw_chunks[-1]["question_type"] == QUESTION_TYPE_STRUCTURED_ESSAY:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue

            elif question_type == QUESTION_TYPE_ESSAY:
                if q_number < 5 or q_number > 9:
                    if raw_chunks and raw_chunks[-1]["question_type"] == QUESTION_TYPE_ESSAY:
                        raw_chunks[-1]["full_text"] += f"\n{q_number}. " + body_clean
                    continue

            # Filter tiny spurious lines
            if len(body_clean) < 12 and not re.search(r"\(\s*[1-4]\s*\)", body_clean):
                continue

            # Ensure clean prefix
            if body_clean.startswith(f"{q_number}."):
                full_q_text = body_clean
            elif body_clean.startswith(f"Question {q_number}."):
                full_q_text = body_clean
            else:
                full_q_text = f"{q_number}. " + body_clean

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

    # Merge duplicate question numbers within the same section if any
    cleaned_chunks = []
    seen_keys = set()
    for c in raw_chunks:
        key = (c["question_type"], c["question_number"])
        if key in seen_keys:
            # Find and merge into existing chunk
            for existing in cleaned_chunks:
                if (existing["question_type"] == c["question_type"] and 
                    existing["question_number"] == c["question_number"]):
                    existing["full_text"] += "\n" + c["full_text"]
                    existing["options"].update(c["options"])
                    if c["has_diagram"]:
                        existing["has_diagram"] = True
                        existing["diagram_description"] = c["diagram_description"]
                        existing["metadata"]["has_diagram"] = True
                        if c["diagram_description"]:
                            existing["metadata"]["diagram_description"] = c["diagram_description"]
                    break
        else:
            seen_keys.add(key)
            cleaned_chunks.append(c)

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