import uuid
from datetime import datetime
from typing import List, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.question import Question
    from app.models.marking_scheme import MarkingScheme

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    filename: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    file_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    year: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    doc_type: Mapped[str] = mapped_column(
        String(50), default="past_paper", nullable=False, index=True
    )  # 'past_paper' | 'textbook' | 'marking_scheme'
    grade: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True
    )
    total_pages: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    subject: Mapped["Subject | None"] = relationship(
        "Subject", back_populates="documents"
    )
    questions: Mapped[List["Question"]] = relationship(
        "Question", back_populates="document", cascade="all, delete-orphan"
    )
    marking_schemes: Mapped[List["MarkingScheme"]] = relationship(
        "MarkingScheme", back_populates="document", cascade="all, delete-orphan"
    )
