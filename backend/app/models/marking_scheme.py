import uuid
from typing import Any, List, TYPE_CHECKING
from sqlalchemy import Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.question import Question

class MarkingScheme(Base, TimestampMixin):
    __tablename__ = "marking_schemes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    model_answer: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    scheme_breakdown: Mapped[List[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )  # e.g., [{"point": "State formula", "marks": 1}, ...]
    total_marks: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document", back_populates="marking_schemes"
    )
    question: Mapped["Question | None"] = relationship(
        "Question", back_populates="marking_schemes"
    )
