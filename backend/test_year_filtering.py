import sys
from app.rag.vectorstore import get_vectorstore
from app.services.rag_service import find_similar_questions, extract_metadata_filters, build_chroma_filter

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def test_metadata_extraction():
    print("=" * 60)
    print("1. TESTING NATURAL LANGUAGE FILTER EXTRACTION")
    print("=" * 60)
    
    test_queries = [
        "Show light questions in 2019",
        "MCQ questions on electricity from 2015 to 2020",
        "Find essay questions on Newton's laws after 2018",
    ]
    
    for q in test_queries:
        cleaned_text, filters = extract_metadata_filters(q)
        chroma_filter = build_chroma_filter(
            start_year=filters.get("start_year"),
            end_year=filters.get("end_year"),
            year=filters.get("year"),
            question_type=filters.get("question_type")
        )
        print(f"Original Query: '{q}'")
        print(f"  -> Cleaned Query : '{cleaned_text}'")
        print(f"  -> Extracted     : {filters}")
        print(f"  -> Chroma Filter : {chroma_filter}\n")


def test_chroma_direct_filtering():
    print("=" * 60)
    print("2. TESTING DIRECT CHROMADB FILTERING (Step 26 Spec)")
    print("=" * 60)
    
    vectorstore = get_vectorstore()
    
    # Step 26 conceptual query:
    # Filter questions between 2018 and 2024
    filter_query = {
        "$and": [
            {"paper_year": {"$gte": 2018}},
            {"paper_year": {"$lte": 2024}},
        ]
    }
    
    query = "light"
    print(f"Direct Chroma similarity search for: '{query}' with filter={filter_query}")
    results = vectorstore.similarity_search(query, k=3, filter=filter_query)
    
    for i, doc in enumerate(results, 1):
        meta = doc.metadata
        print(f"[{i}] Year: {meta.get('paper_year')} | Q{meta.get('question_number')} ({meta.get('question_type')})")
        print(f"    Content: {doc.page_content[:100]}...\n")


def test_service_level_filtering():
    print("=" * 60)
    print("3. TESTING RAG SERVICE FIND_SIMILAR_QUESTIONS")
    print("=" * 60)
    
    # Test natural query with embedded year filter
    natural_query = "Show questions on light between 2018 and 2024"
    print(f"Natural Query: '{natural_query}'")
    results = find_similar_questions(natural_query, limit=3)
    for i, r in enumerate(results, 1):
        print(f"[{i}] Year: {r['year']} | Q{r['question_number']} ({r['question_type']}) | Sim: {r['similarity']}")
        print(f"    Content: {r['question'][:100]}...\n")

    # Test explicit parameter filtering
    print(f"Explicit Parameter Query: topic='electricity', start_year=2015, end_year=2020, question_type='mcq'")
    results_explicit = find_similar_questions("electricity", start_year=2015, end_year=2020, question_type="mcq", limit=3)
    for i, r in enumerate(results_explicit, 1):
        print(f"[{i}] Year: {r['year']} | Q{r['question_number']} ({r['question_type']}) | Sim: {r['similarity']}")
        print(f"    Content: {r['question'][:100]}...\n")


if __name__ == "__main__":
    test_metadata_extraction()
    test_chroma_direct_filtering()
    test_service_level_filtering()
