import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from enum import Enum

class DocumentType(str, Enum):
    PAST_PAPER = "past_paper"
    TEXTBOOK = "textbook"
    MARKING_SCHEME = "marking_scheme"

class DocumentBase(BaseModel):
    filename: str
    year: Optional[int] = None
    doc_type: DocumentType = DocumentType.PAST_PAPER
    grade: Optional[int] = None
    total_pages: Optional[int] = None

class DocumentCreate(DocumentBase):
    file_path: Optional[str] = None
    subject_id: Optional[uuid.UUID] = None

class DocumentResponse(DocumentBase):
    id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    uploaded_at: datetime

    class Config:
        from_attributes = True

class TopicBase(BaseModel):
    name: str
    slug: str
    subject_area: str = "general"
    grade: int = 10
    importance_weight: float = 1.0
    description: Optional[str] = None

class TopicCreate(BaseModel):
    name: str
    subject_area: str = "general"
    grade: int = 10
    description: Optional[str] = None

class TopicResponse(TopicBase):
    id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True
