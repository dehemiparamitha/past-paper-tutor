from app.services.rag_service import ask_question
from fastapi import APIRouter

router = APIRouter()

@router.post("/chat")
def chat(request:dict):
    question = request["question"]
    result = ask_question(question)
    return result