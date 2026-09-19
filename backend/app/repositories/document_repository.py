import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
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

    def list_documents(
        self,
        year: Optional[int] = None,
        subject_id: Optional[uuid.UUID] = None,
        doc_type: Optional[str] = None,
        grade: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Document]:
        stmt = select(Document)
        if year is not None:
            stmt = stmt.where(Document.year == year)
        if subject_id is not None:
            stmt = stmt.where(Document.subject_id == subject_id)
        if doc_type is not None:
            stmt = stmt.where(Document.doc_type == doc_type)
        if grade is not None:
            stmt = stmt.where(Document.grade == grade)

        stmt = stmt.order_by(desc(Document.uploaded_at)).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        filename: str,
        file_path: Optional[str] = None,
        year: Optional[int] = None,
        subject_id: Optional[uuid.UUID] = None,
        doc_type: str = "past_paper",
        grade: Optional[int] = None,
        total_pages: Optional[int] = None,
    ) -> Document:
        doc = Document(
            filename=filename,
            file_path=file_path,
            year=year,
            subject_id=subject_id,
            doc_type=doc_type,
            grade=grade,
            total_pages=total_pages,
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def delete(self, document_id: uuid.UUID) -> bool:
        doc = self.get_by_id(document_id)
        if not doc:
            return False
        self.db.delete(doc)
        self.db.commit()
        return True
