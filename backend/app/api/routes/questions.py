import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.question import QuestionCreate, QuestionResponse
from app.repositories.question_repository import QuestionRepository

router = APIRouter(prefix="/questions", tags=["Questions"])

@router.get("", response_model=List[QuestionResponse])
def list_questions(
    topic_id: Optional[uuid.UUID] = Query(None, description="Filter by topic UUID"),
    topic_slug: Optional[str] = Query(None, description="Filter by topic slug"),
    grade: Optional[int] = Query(None, description="Filter by grade"),
    difficulty: Optional[str] = Query(None, description="easy | medium | hard"),
    question_type: Optional[str] = Query(None, description="mcq | structured_essay | essay"),
    document_id: Optional[uuid.UUID] = Query(None, description="Filter by document UUID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List questions structured in the database with rich filters."""
    repo = QuestionRepository(db)
    questions = repo.list_questions(
        topic_id=topic_id,
        topic_slug=topic_slug,
        grade=grade,
        difficulty=difficulty,
        question_type=question_type,
        document_id=document_id,
        skip=skip,
        limit=limit,
    )
    return [QuestionResponse.model_validate(q) for q in questions]

@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(question_id: uuid.UUID, db: Session = Depends(get_db)):
    """Fetch a single question by ID with marking scheme and topic associations."""
    repo = QuestionRepository(db)
    q = repo.get_by_id(question_id)
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Question with id {question_id} not found",
        )
    return QuestionResponse.model_validate(q)

@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(question_in: QuestionCreate, db: Session = Depends(get_db)):
    """Create a new question entry in the database."""
    repo = QuestionRepository(db)
    q = repo.create(
        document_id=question_in.document_id,
        question_number=question_in.question_number,
        question_text=question_in.question_text,
        marks=question_in.marks,
        difficulty=question_in.difficulty,
        question_type=question_in.question_type,
        options=question_in.options,
        correct_answer=question_in.correct_answer,
        explanation=question_in.explanation,
        topic_ids=question_in.topic_ids,
    )
    return QuestionResponse.model_validate(q)
