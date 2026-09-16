from typing import Optional
from app.services.rag_service import ask_question, find_similar_questions, get_topic_frequency
from fastapi import APIRouter, Query

router = APIRouter()

@router.post("/chat")
def chat(request: dict):
    question = request["question"]
    result = ask_question(question)
    return result

@router.get("/api/questions/similar")
def get_similar_questions(
    query: str = Query(..., min_length=1),
    start_year: Optional[int] = Query(None, ge=1900, le=2100),
    end_year: Optional[int] = Query(None, ge=1900, le=2100),
    year: Optional[int] = Query(None, ge=1900, le=2100),
    question_type: Optional[str] = Query(None),
):
    return {
        "results": find_similar_questions(
            query=query,
            start_year=start_year,
            end_year=end_year,
            year=year,
            question_type=question_type,
        )
    }

@router.get("/api/topics/frequency")
def get_topics_frequency(
    year: Optional[int] = Query(None, ge=1900, le=2100),
    start_year: Optional[int] = Query(None, ge=1900, le=2100),
    end_year: Optional[int] = Query(None, ge=1900, le=2100),
):
    frequencies = get_topic_frequency(
        year=year,
        start_year=start_year,
        end_year=end_year,
    )
    return {
        "total_topics": len(frequencies),
        "frequencies": frequencies,
    }