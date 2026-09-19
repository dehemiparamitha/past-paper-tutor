import uuid
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.question import Question
    from app.models.practice import TopicMastery

class Topic(Base, TimestampMixin):
    __tablename__ = "topics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    slug: Mapped[str] = mapped_column(
        String(150), unique=True, index=True, nullable=False
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    subject_area: Mapped[str] = mapped_column(
        String(50), default="general", nullable=False, index=True
    )  # 'physics' | 'chemistry' | 'biology' | 'general'
    grade: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False, index=True
    )
    importance_weight: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    subject: Mapped["Subject | None"] = relationship(
        "Subject", back_populates="topics"
    )
    questions: Mapped[List["Question"]] = relationship(
        "Question", secondary="question_topics", back_populates="topics"
    )
    masteries: Mapped[List["TopicMastery"]] = relationship(
        "TopicMastery", back_populates="topic", cascade="all, delete-orphan"
    )
