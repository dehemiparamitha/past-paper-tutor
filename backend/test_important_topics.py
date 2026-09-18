import sys
from app.services.rag_service import calculate_important_topics

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def test_important():
    print("=" * 70)
    print("TESTING IMPORTANT TOPICS STATISTICAL ALGORITHM (Step 30)")
    print("=" * 70)

    topics = calculate_important_topics()
    print(f"\nTotal Topics Evaluated: {len(topics)}\n")

    current_tier = None
    for item in topics:
        tier = item["tier"]
        badge = item["badge"]
        if tier != current_tier:
            current_tier = tier
            print(f"\n--- {badge} ---")

        topic = item["topic"]
        score = item["importance_score"]
        b = item["breakdown"]
        q_count = item["total_questions"]
        years = item["years_appeared"]
        total_years = item["total_years_evaluated"]
        subj = item.get("subject_area", "general")
        grade = item.get("grade", 10)

        print(f"[GR {grade} | {subj.upper():<9}] {topic:<42} Score: {score:>3}/100 (Questions: {q_count:>2}, In {years}/{total_years} yrs)")
        print(f"               Breakdown -> Freq: {b['frequency_score']}%, Recency: {b['recency_score']}%, Consistency: {b['consistency_score']}%, Marks: {b['marks_score']}%\n")

if __name__ == "__main__":
    test_important()
