from app.rag.vectorstore import get_vectorstore

# 1. Connect to ChromaDB
vectorstore = get_vectorstore()

# 2. Check total stored questions
total_count = vectorstore._collection.count()
print(f"Total Questions in ChromaDB: {total_count}")

# 3. Test a concept search across past papers
query = "What happens to light rays passing through a convex lens?"
print(f"\nSearching for: '{query}'\n")

results = vectorstore.similarity_search(query, k=2)

for i, doc in enumerate(results, 1):
    meta = doc.metadata
    print(f"[{i}] {meta.get('paper_year', 'Unknown')} Paper | Q{meta.get('question_number')} ({meta.get('question_type')})")
    print(f"    Content: {doc.page_content[:150]}...\n")
