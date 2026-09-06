from app.services.rag_service import ask_question

question = "Find questions about domestic electrical circuits."

answer = ask_question(question)

print("\nAnswer:")
print(answer)