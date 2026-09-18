import os
import re
from typing import List, Dict, Any, Optional
import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from app.rag.topic_extractor import enrich_chunks_with_topics


def extract_grade_from_filename(file_path: str) -> int:
    """Extracts grade number from filename (e.g. grade-10-science.pdf -> 10)."""
    filename = os.path.basename(file_path)
    match = re.search(r"grade[_\-]?(\d+)", filename, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 10


def is_textbook_header_footer(line: str) -> bool:
    """Detects repetitive headers, footers, page numbers, and margin notes in textbooks."""
    clean = line.strip()
    if not clean:
        return True
    
    # Standalone numbers or page indicators
    if re.fullmatch(r"-?\s*\d+\s*-?", clean):
        return True
    
    clean_lower = clean.lower()
    # Reoccurring header/footer phrases in O/L textbooks
    boilerplate = [
        "for free distribution",
        "for knowledge",
        "extra knowledge",
        "science | grade",
        "department of educational publications",
    ]
    for b in boilerplate:
        if b in clean_lower:
            return True

    return False


def load_and_clean_textbook_pages(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extracts text page by page from a textbook PDF, filtering out headers/footers.
    Returns list of page dicts with page_number, clean_text, grade, and source.
    """
    grade = extract_grade_from_filename(pdf_path)
    filename = os.path.basename(pdf_path)
    doc = pymupdf.open(pdf_path)
    pages_data = []

    for page_idx, page in enumerate(doc, start=1):
        raw_text = page.get_text("text")
        if not raw_text.strip():
            continue

        cleaned_lines = []
        for line in raw_text.splitlines():
            if is_textbook_header_footer(line):
                continue
            cleaned_lines.append(line.rstrip())

        page_text = "\n".join(cleaned_lines).strip()
        if page_text:
            pages_data.append({
                "page_number": page_idx,
                "text": page_text,
                "grade": grade,
                "source": filename
            })

    doc.close()
    return pages_data


def chunk_textbook(
    pdf_path: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 150
) -> List[Dict[str, Any]]:
    """
    Loads textbook pages, chunks text using RecursiveCharacterTextSplitter,
    and enriches with syllabus topics.
    """
    pages = load_and_clean_textbook_pages(pdf_path)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = []
    chunk_idx = 0
    grade = extract_grade_from_filename(pdf_path)
    filename = os.path.basename(pdf_path)

    for page_data in pages:
        page_num = page_data["page_number"]
        page_text = page_data["text"]

        splits = splitter.split_text(page_text)
        for split_text in splits:
            split_text = split_text.strip()
            if len(split_text) < 40:  # Skip trivial fragments
                continue

            chunk_idx += 1
            chunks.append({
                "chunk_id": f"textbook_g{grade}_p{page_num}_c{chunk_idx}",
                "stem": split_text,
                "full_text": split_text,
                "page_number": page_num,
                "metadata": {
                    "doc_type": "textbook",
                    "grade": grade,
                    "title": f"Grade {grade} Science Textbook",
                    "source": filename,
                    "page_number": page_num
                }
            })

    if chunks:
        chunks = enrich_chunks_with_topics(chunks, batch_size=15)

    return chunks


def textbook_chunks_to_documents(chunks: List[Dict[str, Any]]) -> List[Document]:
    """Converts textbook chunk dicts to LangChain Document objects."""
    documents = []
    for chunk in chunks:
        doc = Document(
            page_content=chunk["full_text"],
            metadata=chunk["metadata"]
        )
        documents.append(doc)
    return documents
