import sys
from app.services.rag_service import get_topic_frequency

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def test_frequency():
    print("=" * 60)
    print("TESTING TOPIC FREQUENCY ANALYSIS (Step 28)")
    print("=" * 60)

    # 1. Overall frequency across all papers
    print("\n--- Overall Topic Frequency ---")
    results = get_topic_frequency()
    print(f"Total Unique Topics: {len(results)}")
    for item in results:
        print(f"  {item['topic']:<30} : {item['count']}")

    # 2. Filtered frequency by year (e.g. 2018)
    print("\n--- 2018 Topic Frequency ---")
    results_2018 = get_topic_frequency(year=2018)
    print(f"Total Unique Topics in 2018: {len(results_2018)}")
    for item in results_2018:
        print(f"  {item['topic']:<30} : {item['count']}")

if __name__ == "__main__":
    test_frequency()
