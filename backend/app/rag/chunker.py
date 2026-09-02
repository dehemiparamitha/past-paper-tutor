import re
from typing import List, Dict, Any, Optional
from langchain_core.documents import Document


def split_questions(text: str, paper_year: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Splits full PDF extracted text into structured question chunks.

    Handles:
    - Page markers: `--- Page X ---`
    - Question boundary patterns: `1. `, `2. `, `15. `, `Question 1. `
    - Inline diagram tags: `[DIAGRAM: ...]`
    - MCQ options: `(1)`, `(2)`, `(3)`, `(4)`
    """
    # Track current page number while scanning through lines
    pages_text = re.split(r"(?:\n|^)---\s*Page\s+(\d+)\s*---", text, flags=re.IGNORECASE)

    raw_page_blocks = []

    if len(pages_text) > 1:
        if pages_text[0].strip():
            raw_page_blocks.append((1, pages_text[0]))
        for i in range(1, len(pages_text), 2):
            p_num = int(pages_text[i])
            p_content = pages_text[i+1] if i + 1 < len(pages_text) else ""
            raw_page_blocks.append((p_num, p_content))
    else:
        raw_page_blocks.append((1, text))

    chunks = []

    # Regex matches question start numbers (1 to 40) at the start of a line or paragraph
    q_boundary_pattern = re.compile(
        r"(?:\n|^)(?=(?:Question\s+)?([1-9]|[1-3][0-9]|40)\s*[\.\)])",
        re.IGNORECASE
    )

    for p_num, p_content in raw_page_blocks:
        parts = q_boundary_pattern.split(p_content)

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

            # Ensure single question prefix e.g. "3. " instead of "3. 3. "
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
            opt_matches = re.findall(r"\(\s*([1-4])\s*\)\s*([^\(\n]+)", full_q_text)
            for opt_num, opt_val in opt_matches:
                opt_clean = opt_val.strip()
                if opt_clean and opt_num not in options:
                    options[opt_num] = opt_clean

            # Stem text (everything before options)
            first_opt_match = re.search(r"\(\s*[1-4]\s*\)", full_q_text)
            if first_opt_match:
                stem_text = full_q_text[:first_opt_match.start()].strip()
            else:
                stem_text = full_q_text.strip()

            metadata = {
                "question_number": q_number,
                "page_number": p_num,
                "has_diagram": has_diagram,
            }
            if paper_year:
                metadata["paper_year"] = paper_year
            if diagram_description:
                metadata["diagram_description"] = diagram_description

            chunks.append({
                "question_number": q_number,
                "page_number": p_num,
                "has_diagram": has_diagram,
                "diagram_description": diagram_description,
                "stem": stem_text,
                "options": options,
                "full_text": full_q_text,
                "metadata": metadata
            })

    return chunks


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