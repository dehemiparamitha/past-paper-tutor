import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.question import Question
    from app.models.topic import Topic

class PracticeAttempt(Base, TimestampMixin):
    __tablename__ = "practice_attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_answer: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    is_correct: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # 'yes' | 'no' | 'partial'
    marks_awarded: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    total_possible_marks: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )
    percentage: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    ai_feedback: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    user: Mapped["User | None"] = relationship(
        "User", back_populates="practice_attempts"
    )
    question: Mapped["Question"] = relationship(
        "Question", back_populates="attempts"
    )

class TopicMastery(Base, TimestampMixin):
    __tablename__ = "topic_masteries"
    __table_args__ = (
        UniqueConstraint("user_id", "topic_id", name="uq_user_topic_mastery"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempts_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    correct_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    mastery_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )  # 0.0 to 100.0
    last_practiced_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="topic_masteries"
    )
    topic: Mapped["Topic"] = relationship(
        "Topic", back_populates="masteries"
    )
