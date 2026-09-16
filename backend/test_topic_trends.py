import sys
from app.services.rag_service import get_topic_trends

try:
    sys.stdout.reconfigure(encoding='utf-8')
except AttributeError:
    pass

def test_trends():
    print("=" * 65)
    print("TESTING TOPIC HISTORICAL TRENDS (Step 29)")
    print("=" * 65)

    all_trends = get_topic_trends()
    print(f"\nTotal Topics with Trend Data: {len(all_trends)}\n")

    # Display top 8 topics with their yearly distributions and trend indicator
    for item in all_trends[:8]:
        topic = item["topic"]
        total = item["total_questions"]
        trend = item["trend"]
        subj = item.get("subject_area", "general")
        breakdown = item["yearly_breakdown"]

        # Format visual timeline
        timeline_str = " | ".join([f"{y}: {c}" for y, c in sorted(breakdown.items())])

        trend_icon = "📈" if trend == "rising" else ("📉" if trend == "declining" else "📊")
        print(f"[{subj.upper()}] {topic} (Total: {total}) {trend_icon} Trend: {trend.upper()}")
        print(f"   Distribution: {timeline_str}\n")

if __name__ == "__main__":
    test_trends()
