import sys
from app.rag.vectorstore import get_vectorstore
from app.services.rag_service import retrieve_textbook_content, find_similar_questions

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass


def verify_retrieval(query: str, k: int = 3):
    """
    Tests and prints retrieval results for both Textbooks and Past Paper Questions
    for a given search query.
    """
    print("\n" + "=" * 70)
    print(f"SEARCH QUERY: '{query}'")
    print("=" * 70)

    # 1. Test Textbook Theory Retrieval
    print(f"\n--- [1] TEXTBOOK THEORY RETRIEVAL (Top {k} results) ---")
    textbook_results = retrieve_textbook_content(query, k=k)
    if not textbook_results:
        print("  [Warning] No textbook results found.")
    else:
        for i, r in enumerate(textbook_results, 1):
            grade = r.get("grade", "N/A")
            page = r.get("page_number", "N/A")
            source = r.get("source", "N/A")
            topic = r.get("topic", "N/A")
            snippet = r.get("content", "").strip().replace("\n", " ")[:180]
            print(f"  Result #{i}: [Grade {grade} Textbook | Page {page} | Topic: {topic}]")
            print(f"  Source : {source}")
            print(f"  Snippet: \"{snippet}...\"\n")

    # 2. Test Past Paper Questions Retrieval
    print(f"--- [2] PAST PAPER QUESTIONS RETRIEVAL (Top {k} results) ---")
    question_results = find_similar_questions(query, limit=k)
    if not question_results:
        print("  [Warning] No past paper questions found.")
    else:
        for i, q in enumerate(question_results, 1):
            year = q.get("year", "N/A")
            q_num = q.get("question_number", "N/A")
            q_type = (q.get("question_type") or "N/A").upper()
            score = q.get("similarity", 0.0)
            snippet = q.get("question", "").strip().replace("\n", " ")[:180]
            print(f"  Result #{i}: [{year} Paper | {q_type} Q{q_num} | Similarity: {score}]")
            print(f"  Snippet: \"{snippet}...\"\n")


def run_all_tests():
    vectorstore = get_vectorstore()
    total_docs = vectorstore._collection.count()
    print("=" * 70)
    print(f"CHROMADB RETRIEVAL VERIFICATION | Total Documents Stored: {total_docs}")
    print("=" * 70)

    # Sample queries across Physics, Chemistry, Biology
    test_queries = [
        "light refraction convex lens focal point",
        "atomic structure periodic table isotopes",
        "photosynthesis plant transpiration cell"
    ]

    for q in test_queries:
        verify_retrieval(q, k=2)


if __name__ == "__main__":
    run_all_tests()
