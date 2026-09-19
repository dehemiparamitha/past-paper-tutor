import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.document import (
    DocumentCreate, DocumentResponse,
    TopicResponse, TopicCreate,
)
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["Documents & Topics"])

@router.get("", response_model=List[DocumentResponse])
def list_documents(
    year: Optional[int] = Query(None, description="Filter by past paper year"),
    doc_type: Optional[str] = Query(None, description="Filter by document type (e.g. past_paper, textbook)"),
    grade: Optional[int] = Query(None, description="Filter by grade (10, 11)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve all ingested syllabus documents and past papers."""
    service = DocumentService(db)
    return service.list_documents(year=year, doc_type=doc_type, grade=grade, skip=skip, limit=limit)

@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def register_document(doc_in: DocumentCreate, db: Session = Depends(get_db)):
    """Register document metadata in PostgreSQL."""
    service = DocumentService(db)
    return service.register_document(doc_in)

@router.get("/topics", response_model=List[TopicResponse])
def list_topics(
    subject_area: Optional[str] = Query(None, description="Filter by subject area: physics, chemistry, biology"),
    grade: Optional[int] = Query(None, description="Filter by grade (10, 11)"),
    db: Session = Depends(get_db),
):
    """List all registered syllabus topics."""
    service = DocumentService(db)
    return service.list_topics(subject_area=subject_area, grade=grade)

@router.post("/topics", response_model=TopicResponse, status_code=status.HTTP_201_CREATED)
def create_topic(topic_in: TopicCreate, db: Session = Depends(get_db)):
    """Add a new syllabus topic."""
    service = DocumentService(db)
    topic = service.get_or_create_topic(
        name=topic_in.name,
        subject_area=topic_in.subject_area,
        grade=topic_in.grade,
        description=topic_in.description,
    )
    return TopicResponse.model_validate(topic)
