from app.rag.topic_extractor import classify_questions_batch

sample_questions = [
    "A convex lens is used to read a small label. Where should the object be placed to obtain a magnified virtual image?",
]

results = classify_questions_batch(sample_questions)
for r in results:
    print(r)
