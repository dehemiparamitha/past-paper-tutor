import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.practice_service import (
    generate_practice_questions,
    evaluate_student_answer,
    record_practice_attempt,
)
from app.services.rag_service import TOPIC_METADATA_REGISTRY

router = APIRouter(prefix="/api/practice", tags=["Practice Questions"])


class PracticeGenerateRequest(BaseModel):
    topic: str = Field(..., description="Syllabus topic or keyword (e.g. 'photosynthesis', 'geometrical_optics')")
    grade: Optional[int] = Field(None, ge=10, le=11, description="Grade level (10 or 11)")
    subject_area: Optional[str] = Field(None, description="Subject area: 'physics', 'chemistry', or 'biology'")
    question_type: str = Field("mcq", description="Question format: 'mcq', 'structured_essay', or 'essay'")
    difficulty: str = Field("medium", description="Difficulty level: 'easy', 'medium', or 'hard'")
    count: int = Field(3, ge=1, le=10, description="Number of questions to generate (1 to 10)")


class PracticeEvaluateRequest(BaseModel):
    question: str = Field(..., description="The question text")
    student_answer: str = Field(..., description="Student's submitted answer")
    model_answer: str = Field(..., description="Model answer key")
    question_type: str = Field("mcq", description="Format of question ('mcq', 'structured_essay', 'essay')")
    marking_scheme: Optional[List[Dict[str, Any]]] = Field(None, description="Detailed marking breakdown")
    total_marks: int = Field(1, ge=1, description="Maximum total marks possible")
    question_id: Optional[str] = Field(None, description="Optional UUID of the question for tracking")


@router.post("/generate")
def generate_questions(request: PracticeGenerateRequest):
    """
    Generates new practice questions grounded in textbook theory and past paper exam styles.
    """
    result = generate_practice_questions(
        topic=request.topic,
        grade=request.grade,
        subject_area=request.subject_area,
        question_type=request.question_type,
        difficulty=request.difficulty,
        count=request.count,
    )
    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to generate practice questions."))
    return result


@router.post("/evaluate")
def evaluate_answer(request: PracticeEvaluateRequest, db: Session = Depends(get_db)):
    """
    Evaluates a student's answer against the question's model answer and marking scheme,
    and optionally records the attempt if question_id is provided.
    """
    result = evaluate_student_answer(
        question=request.question,
        student_answer=request.student_answer,
        model_answer=request.model_answer,
        question_type=request.question_type,
        marking_scheme=request.marking_scheme,
        total_marks=request.total_marks,
    )

    if request.question_id:
        record_practice_attempt(
            db=db,
            question_id=request.question_id,
            student_answer=request.student_answer,
            evaluation_result=result,
        )

    return result


@router.get("/topics")
def get_practice_topics():
    """
    Returns all officially indexed syllabus topics grouped by Grade and Subject Area.
    """
    topics_list = []
    for topic_key, info in TOPIC_METADATA_REGISTRY.items():
        topics_list.append({
            "key": topic_key,
            "display_name": topic_key.replace("_", " ").title(),
            "grade": info.get("grade", 10),
            "subject_area": info.get("subject_area", "general"),
        })
    return {
        "total_topics": len(topics_list),
        "topics": sorted(topics_list, key=lambda x: (x["grade"], x["subject_area"], x["display_name"]))
    }
