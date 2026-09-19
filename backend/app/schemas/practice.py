import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel

class PracticeAttemptCreate(BaseModel):
    question_id: uuid.UUID
    student_answer: str

class PracticeAttemptResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    student_answer: Optional[str] = None
    is_correct: Optional[str] = None
    marks_awarded: float
    total_possible_marks: float
    percentage: float
    ai_feedback: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TopicMasteryResponse(BaseModel):
    topic_id: uuid.UUID
    topic_name: str
    subject_area: str
    grade: int
    attempts_count: int
    correct_count: int
    mastery_score: float
    last_practiced_at: datetime

    class Config:
        from_attributes = True
