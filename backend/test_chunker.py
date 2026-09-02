import sys
from app.rag.loader import load_pdf
from app.rag.chunker import split_questions, chunks_to_langchain_documents

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

pdf_path = "data/past_papers/2025.pdf"
print(f"Loading {pdf_path}...")
text = load_pdf(pdf_path)

print("\nSplitting questions...")
chunks = split_questions(text, paper_year=2025)

print(f"\nSuccessfully extracted {len(chunks)} question chunks!")

# Print first 5 chunks
for i, chunk in enumerate(chunks[:5], start=1):
    print("\n" + "=" * 80)
    print(f"CHUNK {i} | Question {chunk['question_number']} | Page {chunk['page_number']} | Has Diagram: {chunk['has_diagram']}")
    print("-" * 80)
    print("Full Text:")
    print(chunk["full_text"])
    print("-" * 40)
    print("Options:", chunk["options"])
    print("Metadata:", chunk["metadata"])

# Test LangChain document conversion
docs = chunks_to_langchain_documents(chunks)
print(f"\nConverted {len(docs)} chunks to LangChain Documents.")