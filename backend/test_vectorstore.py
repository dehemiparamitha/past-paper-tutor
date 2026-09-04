from app.rag.vectorstore import get_vectorstore
from langchain_core.documents import Document

# 1. Connect to vectorstore
vectorstore = get_vectorstore()

# 2. Add sample documents (or pass docs from chunker)
docs = [
    Document(
        page_content="Light rays passing through a convex lens converge at the focal point.",
        metadata={"paper_year": 2025, "question_number": 7, "question_type": "essay"}
    )
]
vectorstore.add_documents(docs)

# 3. Perform similarity search
results = vectorstore.similarity_search("How do convex lenses work with light rays?", k=1)
for doc in results:
    print("Found Document:", doc.page_content)
    print("Metadata:", doc.metadata)
