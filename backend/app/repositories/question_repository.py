import uuid
from typing import Optional, List, Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, desc
from app.models.question import Question, question_topics
from app.models.topic import Topic
from app.models.document import Document

class QuestionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, question_id: uuid.UUID) -> Optional[Question]:
        stmt = (
            select(Question)
            .options(
                selectinload(Question.topics),
                selectinload(Question.document),
                selectinload(Question.marking_schemes),
            )
            .where(Question.id == question_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_questions(
        self,
        topic_id: Optional[uuid.UUID] = None,
        topic_slug: Optional[str] = None,
        grade: Optional[int] = None,
        difficulty: Optional[str] = None,
        question_type: Optional[str] = None,
        document_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Question]:
        stmt = (
            select(Question)
            .options(
                selectinload(Question.topics),
                selectinload(Question.document),
            )
            .distinct()
        )

        if topic_id is not None:
            stmt = stmt.join(Question.topics).where(Topic.id == topic_id)
        elif topic_slug is not None:
            stmt = stmt.join(Question.topics).where(Topic.slug == topic_slug)

        if grade is not None:
            stmt = stmt.join(Question.document).where(Document.grade == grade)

        if difficulty is not None and difficulty != "all":
            stmt = stmt.where(Question.difficulty == difficulty.lower())

        if question_type is not None and question_type != "all":
            stmt = stmt.where(Question.question_type == question_type.lower())

        if document_id is not None:
            stmt = stmt.where(Question.document_id == document_id)

        stmt = stmt.order_by(desc(Question.created_at)).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        document_id: uuid.UUID,
        question_number: str,
        question_text: str,
        marks: int = 1,
        difficulty: str = "medium",
        question_type: str = "mcq",
        options: Optional[List[str]] = None,
        correct_answer: Optional[str] = None,
        explanation: Optional[str] = None,
        topic_ids: Optional[List[uuid.UUID]] = None,
    ) -> Question:
        question = Question(
            document_id=document_id,
            question_number=question_number,
            question_text=question_text,
            marks=marks,
            difficulty=difficulty,
            question_type=question_type,
            options=options,
            correct_answer=correct_answer,
            explanation=explanation,
        )
        self.db.add(question)
        self.db.flush()

        if topic_ids:
            topics = self.db.execute(
                select(Topic).where(Topic.id.in_(topic_ids))
            ).scalars().all()
            question.topics.extend(topics)

        self.db.commit()
        self.db.refresh(question)
        return question
