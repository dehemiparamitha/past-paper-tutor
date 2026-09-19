import uuid
from typing import List, Any, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, ForeignKey, Table, Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.topic import Topic
    from app.models.marking_scheme import MarkingScheme
    from app.models.practice import PracticeAttempt

# Association Table for Many-to-Many Question <-> Topic
question_topics = Table(
    "question_topics",
    Base.metadata,
    Column(
        "question_id",
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "topic_id",
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

class Question(Base, TimestampMixin):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_number: Mapped[str] = mapped_column(
        String(20), nullable=False
    )
    question_text: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    marks: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    difficulty: Mapped[str] = mapped_column(
        String(20), default="medium", nullable=False, index=True
    )  # 'easy' | 'medium' | 'hard'
    question_type: Mapped[str] = mapped_column(
        String(30), default="mcq", nullable=False, index=True
    )  # 'mcq' | 'structured_essay' | 'essay'
    options: Mapped[List[str] | None] = mapped_column(
        JSONB, nullable=True
    )
    correct_answer: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    explanation: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="questions"
    )
    topics: Mapped[List["Topic"]] = relationship(
        "Topic", secondary=question_topics, back_populates="questions"
    )
    marking_schemes: Mapped[List["MarkingScheme"]] = relationship(
        "MarkingScheme", back_populates="question", cascade="all, delete-orphan"
    )
    attempts: Mapped[List["PracticeAttempt"]] = relationship(
        "PracticeAttempt", back_populates="question", cascade="all, delete-orphan"
    )
