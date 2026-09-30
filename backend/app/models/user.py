import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.chat import ChatSession
    from app.models.practice import PracticeAttempt, TopicMastery

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    full_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    grade: Mapped[int] = mapped_column(
        Integer, default=11, nullable=False
    )
    target_exam: Mapped[str] = mapped_column(
        String(50), default="GCE O/L", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    language: Mapped[str | None] = mapped_column(
        String(50), default="English", nullable=True
    )
    school: Mapped[str | None] = mapped_column(
        String(150), nullable=True
    )
    district: Mapped[str | None] = mapped_column(
        String(100), default="Colombo", nullable=True
    )
    study_goal: Mapped[str | None] = mapped_column(
        String(100), default="Finals prep", nullable=True
    )
    weekly_hours: Mapped[str | None] = mapped_column(
        String(50), default="5 hours a week", nullable=True
    )
    study_time: Mapped[str | None] = mapped_column(
        String(50), default="Weekdays at 7 PM", nullable=True
    )
    confidence_level: Mapped[str | None] = mapped_column(
        String(50), default="Finding my footing", nullable=True
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    # Relationships
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )
    practice_attempts: Mapped[List["PracticeAttempt"]] = relationship(
        "PracticeAttempt", back_populates="user", cascade="all, delete-orphan"
    )
    topic_masteries: Mapped[List["TopicMastery"]] = relationship(
        "TopicMastery", back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[List["RefreshToken"]] = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan"
    )

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token: Mapped[str] = mapped_column(
        Text, unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    is_revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationship
    user: Mapped["User"] = relationship(
        "User", back_populates="refresh_tokens"
    )
