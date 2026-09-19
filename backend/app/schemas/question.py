import uuid
from typing import Optional, List, Any
from pydantic import BaseModel
from app.schemas.document import TopicResponse

class QuestionBase(BaseModel):
    question_number: str
    question_text: str
    marks: int = 1
    difficulty: str = "medium"  # 'easy' | 'medium' | 'hard'
    question_type: str = "mcq"  # 'mcq' | 'structured_essay' | 'essay'
    options: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None

class QuestionCreate(QuestionBase):
    document_id: uuid.UUID
    topic_ids: Optional[List[uuid.UUID]] = None

class MarkingSchemeResponse(BaseModel):
    id: uuid.UUID
    model_answer: Optional[str] = None
    scheme_breakdown: Optional[List[dict[str, Any]]] = None
    total_marks: int = 1

    class Config:
        from_attributes = True

class QuestionResponse(QuestionBase):
    id: uuid.UUID
    document_id: uuid.UUID
    topics: List[TopicResponse] = []
    marking_schemes: List[MarkingSchemeResponse] = []

    class Config:
        from_attributes = True
