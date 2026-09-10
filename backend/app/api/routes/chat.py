from app.services.rag_service import ask_question, find_similar_questions
from fastapi import APIRouter, Query

router = APIRouter()

@router.post("/chat")
def chat(request:dict):
    question = request["question"]
    result = ask_question(question)
    return result

@router.get("/api/questions/similar")
def get_similar_questions(query: str = Query(..., min_length=1)):
    return {"results": find_similar_questions(query)}