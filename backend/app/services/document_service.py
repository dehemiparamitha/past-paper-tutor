import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.topic import Topic
from app.models.question import Question
from app.repositories.document_repository import DocumentRepository
from app.repositories.topic_repository import TopicRepository
from app.repositories.question_repository import QuestionRepository
from app.schemas.document import DocumentCreate, DocumentResponse, TopicResponse

class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.doc_repo = DocumentRepository(db)
        self.topic_repo = TopicRepository(db)
        self.question_repo = QuestionRepository(db)

    def list_documents(
        self,
        year: Optional[int] = None,
        doc_type: Optional[str] = None,
        grade: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[DocumentResponse]:
        docs = self.doc_repo.list_documents(
            year=year, doc_type=doc_type, grade=grade, skip=skip, limit=limit
        )
        return [DocumentResponse.model_validate(d) for d in docs]

    def register_document(self, doc_in: DocumentCreate) -> DocumentResponse:
        existing = self.doc_repo.get_by_filename(doc_in.filename)
        if existing:
            return DocumentResponse.model_validate(existing)

        doc = self.doc_repo.create(
            filename=doc_in.filename,
            file_path=doc_in.file_path,
            year=doc_in.year,
            subject_id=doc_in.subject_id,
            doc_type=doc_in.doc_type,
            grade=doc_in.grade,
            total_pages=doc_in.total_pages,
        )
        return DocumentResponse.model_validate(doc)

    def list_topics(
        self,
        subject_area: Optional[str] = None,
        grade: Optional[int] = None,
    ) -> List[TopicResponse]:
        topics = self.topic_repo.list_topics(subject_area=subject_area, grade=grade)
        return [TopicResponse.model_validate(t) for t in topics]

    def get_or_create_topic(
        self,
        name: str,
        subject_area: str = "general",
        grade: int = 10,
        description: Optional[str] = None,
    ) -> Topic:
        return self.topic_repo.get_or_create(
            name=name,
            subject_area=subject_area,
            grade=grade,
            description=description,
        )
