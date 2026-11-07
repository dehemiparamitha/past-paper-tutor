import uuid
from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, func
from app.models.document import Document

class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, document_id: uuid.UUID) -> Optional[Document]:
        return self.db.execute(
            select(Document).where(Document.id == document_id)
        ).scalar_one_or_none()

    def get_by_filename(self, filename: str) -> Optional[Document]:
        return self.db.execute(
            select(Document).where(Document.filename == filename)
        ).scalar_one_or_none()

    def _build_filter_stmt(
        self,
        search: Optional[str] = None,
        year: Optional[int] = None,
        subject_id: Optional[uuid.UUID] = None,
        doc_type: Optional[str] = None,
        grade: Optional[int] = None,
        processing_status: Optional[str] = None,
    ):
        stmt = select(Document)
        if search:
            stmt = stmt.where(Document.filename.ilike(f"%{search.strip()}%"))
        if year is not None:
            stmt = stmt.where(Document.year == year)
        if subject_id is not None:
            stmt = stmt.where(Document.subject_id == subject_id)
        if doc_type is not None:
            stmt = stmt.where(Document.doc_type == doc_type)
        if grade is not None:
            stmt = stmt.where(Document.grade == grade)
        if processing_status is not None:
            stmt = stmt.where(Document.processing_status == processing_status)
        return stmt

    def list_documents(
        self,
        search: Optional[str] = None,
        year: Optional[int] = None,
        subject_id: Optional[uuid.UUID] = None,
        doc_type: Optional[str] = None,
        grade: Optional[int] = None,
        processing_status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        stmt = self._build_filter_stmt(
            search=search,
            year=year,
            subject_id=subject_id,
            doc_type=doc_type,
            grade=grade,
            processing_status=processing_status,
        )
        stmt = stmt.order_by(desc(Document.uploaded_at)).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count_documents(
        self,
        search: Optional[str] = None,
        year: Optional[int] = None,
        subject_id: Optional[uuid.UUID] = None,
        doc_type: Optional[str] = None,
        grade: Optional[int] = None,
        processing_status: Optional[str] = None,
    ) -> int:
        stmt = select(func.count(Document.id))
        if search:
            stmt = stmt.where(Document.filename.ilike(f"%{search.strip()}%"))
        if year is not None:
            stmt = stmt.where(Document.year == year)
        if subject_id is not None:
            stmt = stmt.where(Document.subject_id == subject_id)
        if doc_type is not None:
            stmt = stmt.where(Document.doc_type == doc_type)
        if grade is not None:
            stmt = stmt.where(Document.grade == grade)
        if processing_status is not None:
            stmt = stmt.where(Document.processing_status == processing_status)
        return self.db.execute(stmt).scalar() or 0

    def create(
        self,
        filename: str,
        file_path: Optional[str] = None,
        year: Optional[int] = None,
        subject_id: Optional[uuid.UUID] = None,
        doc_type: str = "past_paper",
        grade: Optional[int] = None,
        total_pages: Optional[int] = None,
        processing_status: str = "UPLOADED",
        processing_error: Optional[str] = None,
        processed_at: Optional[datetime] = None,
    ) -> Document:
        doc = Document(
            filename=filename,
            file_path=file_path,
            year=year,
            subject_id=subject_id,
            doc_type=doc_type,
            grade=grade,
            total_pages=total_pages,
            processing_status=processing_status,
            processing_error=processing_error,
            processed_at=processed_at,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update_status(
        self,
        document_id: uuid.UUID,
        status: str,
        error: Optional[str] = None,
        total_pages: Optional[int] = None,
        processed_at: Optional[datetime] = None,
    ) -> Optional[Document]:
        doc = self.get_by_id(document_id)
        if not doc:
            return None
        doc.processing_status = status
        doc.processing_error = error
        if total_pages is not None:
            doc.total_pages = total_pages
        if processed_at is not None:
            doc.processed_at = processed_at
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def delete(self, document_id: uuid.UUID) -> bool:
        doc = self.get_by_id(document_id)
        if not doc:
            return False
        # Use expunge + direct SQL DELETE to avoid ORM lazy-loading related
        # tables (questions, marking_schemes) during cascade resolution.
        # The FK ON DELETE CASCADE in PostgreSQL handles child row cleanup.
        self.db.expunge(doc)
        from sqlalchemy import delete as sa_delete
        self.db.execute(sa_delete(type(doc)).where(type(doc).id == document_id))
        self.db.commit()
        return True
