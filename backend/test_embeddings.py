from app.rag.embeddings import get_embeddings

embeddings = get_embeddings()

# text = "Explain Dijkstra's algorithm."

# vector = embeddings.embed_query(text)

# print("Vector length:", len(vector))
# print("First 10 values:", vector[:10])

questions = [
    "Explain Dijkstra's algorithm.",
    "What is recursion?",
    "Explain binary search trees."
]

for question in questions:
    vector = embeddings.embed_query(question)

    print(question)
    print("Vector length:", len(vector))