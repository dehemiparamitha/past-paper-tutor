import os
import sys
import glob
from typing import List, Optional
from app.rag.loader import load_pdf
from app.rag.chunker import split_questions, chunks_to_langchain_documents
from app.rag.vectorstore import get_vectorstore

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass


def ingest_paper(pdf_path: str, vectorstore) -> int:
    """
    Loads, chunks, and ingests a single past paper PDF into ChromaDB.
    Returns the number of question documents added.
    """
    filename = os.path.basename(pdf_path)
    print(f"\nProcessing: {filename}")
    
    # 1. Load PDF text (OCR + Diagram descriptions)
    text = load_pdf(pdf_path)
    if not text.strip():
        print(f"Warning: No text extracted from {filename}")
        return 0

    # 2. Chunk questions
    chunks = split_questions(text, file_path=pdf_path)
    if not chunks:
        print(f"Warning: No question chunks found in {filename}")
        return 0

    # 3. Convert to LangChain Document objects
    docs = chunks_to_langchain_documents(chunks)

    # 4. Generate deterministic, unique IDs for each question chunk
    # Format: e.g. "2025_mcq_q1", "2025_structured_essay_q2", "2025_essay_q5"
    doc_ids = [
        f"{c['metadata'].get('paper_year', 'unknown')}_{c['question_type']}_q{c['question_number']}"
        for c in chunks
    ]
    print(f"Extracted {len(docs)} question chunks ({chunks[0]['metadata'].get('paper_year', 'Unknown')} Paper)")

    # 5. Ingest into ChromaDB using unique IDs
    vectorstore.add_documents(docs, ids=doc_ids)
    print(f"Successfully stored {len(docs)} documents into ChromaDB.")
    return len(docs)


def ingest_all(target_file: Optional[str] = None, reset: bool = False):
    """
    Ingests all PDFs in data/past_papers/ or a specific PDF if provided.
    """
    print("=" * 60)
    print("STARTING PAST PAPER DATA INGESTION")
    print("=" * 60)

    # Initialize ChromaDB connection
    vectorstore = get_vectorstore()

    # Optional: Reset collection if --reset flag is passed
    if reset:
        print("Clearing existing ChromaDB collection...")
        vectorstore.reset_collection()

    if target_file and target_file != "--reset":
        if os.path.exists(target_file):
            pdf_files = [target_file]
        else:
            candidate = os.path.join("data", "past_papers", os.path.basename(target_file))
            if not candidate.endswith(".pdf"):
                candidate += ".pdf"
            if os.path.exists(candidate):
                pdf_files = [candidate]
            else:
                print(f"Error: File '{target_file}' not found.")
                return
    else:
        pdf_files = sorted(glob.glob("data/past_papers/*.pdf"))

    if not pdf_files:
        print("No PDF files found in 'data/past_papers/'.")
        return

    print(f"Found {len(pdf_files)} paper(s) to ingest.\n")

    total_chunks = 0
    for pdf_path in pdf_files:
        try:
            count = ingest_paper(pdf_path, vectorstore)
            total_chunks += count
        except Exception as e:
            print(f"Error ingesting {pdf_path}: {e}")

    current_total = vectorstore._collection.count()
    print("\n" + "=" * 60)
    print(f"INGESTION COMPLETE: {current_total} unique questions currently stored in ChromaDB")
    print("=" * 60)


if __name__ == "__main__":
    args = sys.argv[1:]
    reset_flag = "--reset" in args
    paper_arg = next((a for a in args if a != "--reset"), None)
    ingest_all(target_file=paper_arg, reset=reset_flag)
