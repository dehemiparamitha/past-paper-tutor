from app.rag.topic_extractor import classify_questions_batch

sample_questions = [
    "A convex lens is used to read a small label. Where should the object be placed to obtain a magnified virtual image?",
    "Calculate the mass of sodium hydroxide (NaOH) required to prepare a 250 cm3 solution of concentration 0.5 mol dm-3.",
    "Which blood vessel carries oxygenated blood from the lungs to the left atrium of the human heart?",
    "An electric iron of power 1200 W is used for 30 minutes. Calculate the electrical energy consumed in kilowatt-hours (kWh).",
    "State two observations when a piece of magnesium ribbon is added to a test tube containing dilute hydrochloric acid."
]

print("=" * 60)
print("TESTING O/L SCIENCE SYLLABUS TOPIC CLASSIFICATION")
print("=" * 60)

results = classify_questions_batch(sample_questions)
for r in results:
    print(f"[{r.get('subject_area', '').upper()}] Topic: {r.get('topic')} | Subtopic: {r.get('subtopic')}")
    print(f"  Keywords: {r.get('keywords')}\n")
