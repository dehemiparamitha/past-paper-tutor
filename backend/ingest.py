import os
import sys
import glob
from typing import List, Optional
from app.rag.loader import load_pdf
from app.rag.chunker import split_questions, chunks_to_langchain_documents
from app.rag.textbook_loader import chunk_textbook, textbook_chunks_to_documents
from app.rag.vectorstore import get_vectorstore
from app.rag.topic_extractor import enrich_chunks_with_topics

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
    print(f"\nProcessing Past Paper: {filename}")
    
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

    # Ensure doc_type metadata tag is set
    for c in chunks:
        c["metadata"]["doc_type"] = "past_paper"

    # 3. Automatic LLM topic classification
    chunks = enrich_chunks_with_topics(chunks)

    # 4. Convert to LangChain Document objects
    docs = chunks_to_langchain_documents(chunks)

    # 5. Generate deterministic, unique IDs for each question chunk
    doc_ids = [
        f"paper_{c['metadata'].get('paper_year', 'unknown')}_{c['question_type']}_q{c['question_number']}"
        for c in chunks
    ]
    print(f"Extracted {len(docs)} question chunks ({chunks[0]['metadata'].get('paper_year', 'Unknown')} Paper)")

    # 6. Ingest into ChromaDB using unique IDs
    vectorstore.add_documents(docs, ids=doc_ids)
    print(f"Successfully stored {len(docs)} past paper documents into ChromaDB.")
    return len(docs)


def ingest_textbook(pdf_path: str, vectorstore) -> int:
    """
    Loads, chunks, enriches, and ingests a textbook PDF into ChromaDB.
    Returns the number of textbook chunks added.
    """
    filename = os.path.basename(pdf_path)
    print(f"\nProcessing Textbook: {filename}")

    # 1. Chunk and enrich textbook text
    chunks = chunk_textbook(pdf_path)
    if not chunks:
        print(f"Warning: No text chunks generated from {filename}")
        return 0

    # 2. Convert to LangChain Document objects
    docs = textbook_chunks_to_documents(chunks)

    # 3. Generate IDs
    doc_ids = [c["chunk_id"] for c in chunks]
    print(f"Extracted {len(docs)} textbook chunks from {filename}")

    # 4. Ingest into ChromaDB
    vectorstore.add_documents(docs, ids=doc_ids)
    print(f"Successfully stored {len(docs)} textbook chunks into ChromaDB.")
    return len(docs)


def ingest_all(
    target_file: Optional[str] = None,
    reset: bool = False,
    include_textbooks: bool = False,
    textbooks_only: bool = False
):
    """
    Ingests PDFs into ChromaDB.
    """
    print("=" * 60)
    print("STARTING DATA INGESTION INTO CHROMADB")
    print("=" * 60)

    # Initialize ChromaDB connection
    vectorstore = get_vectorstore()

    # Optional: Reset collection if --reset flag is passed
    if reset:
        print("Clearing existing ChromaDB collection...")
        vectorstore.reset_collection()

    paper_files = []
    textbook_files = []

    if target_file and not target_file.startswith("--"):
        if os.path.exists(target_file):
            if "text_book" in target_file.lower() or "textbook" in target_file.lower():
                textbook_files = [target_file]
            else:
                paper_files = [target_file]
        else:
            # Check candidate paths
            cand_paper = os.path.join("data", "past_papers", os.path.basename(target_file))
            cand_book = os.path.join("data", "text_books", os.path.basename(target_file))
            if not cand_paper.endswith(".pdf"):
                cand_paper += ".pdf"
            if not cand_book.endswith(".pdf"):
                cand_book += ".pdf"

            if os.path.exists(cand_book):
                textbook_files = [cand_book]
            elif os.path.exists(cand_paper):
                paper_files = [cand_paper]
            else:
                print(f"Error: File '{target_file}' not found.")
                return
    else:
        if not textbooks_only:
            paper_files = sorted(glob.glob("data/past_papers/*.pdf"))
        if include_textbooks or textbooks_only:
            textbook_files = sorted(glob.glob("data/text_books/*.pdf"))

    print(f"Found {len(paper_files)} paper(s) and {len(textbook_files)} textbook(s) to ingest.\n")

    total_chunks = 0

    for pdf_path in paper_files:
        try:
            count = ingest_paper(pdf_path, vectorstore)
            total_chunks += count
        except Exception as e:
            print(f"Error ingesting paper {pdf_path}: {e}")

    for pdf_path in textbook_files:
        try:
            count = ingest_textbook(pdf_path, vectorstore)
            total_chunks += count
        except Exception as e:
            print(f"Error ingesting textbook {pdf_path}: {e}")

    current_total = vectorstore._collection.count()
    print("\n" + "=" * 60)
    print(f"INGESTION COMPLETE: {current_total} total documents currently stored in ChromaDB")
    print("=" * 60)


if __name__ == "__main__":
    args = sys.argv[1:]
    reset_flag = "--reset" in args
    include_textbooks = "--all" in args or "--textbooks" in args
    textbooks_only = "--textbooks" in args and "--all" not in args
    target_arg = next((a for a in args if not a.startswith("--")), None)

    ingest_all(
        target_file=target_arg,
        reset=reset_flag,
        include_textbooks=include_textbooks,
        textbooks_only=textbooks_only
    )

