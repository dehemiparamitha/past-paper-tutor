import uuid
import re
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.models.topic import Topic

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '_', text)

class TopicRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, topic_id: uuid.UUID) -> Optional[Topic]:
        return self.db.execute(
            select(Topic).where(Topic.id == topic_id)
        ).scalar_one_or_none()

    def get_by_name(self, name: str) -> Optional[Topic]:
        return self.db.execute(
            select(Topic).where(func.lower(Topic.name) == name.lower().strip())
        ).scalar_one_or_none()

    def get_by_slug(self, slug: str) -> Optional[Topic]:
        return self.db.execute(
            select(Topic).where(Topic.slug == slug.lower().strip())
        ).scalar_one_or_none()

    def list_topics(
        self,
        subject_id: Optional[uuid.UUID] = None,
        subject_area: Optional[str] = None,
        grade: Optional[int] = None,
    ) -> List[Topic]:
        stmt = select(Topic)
        if subject_id is not None:
            stmt = stmt.where(Topic.subject_id == subject_id)
        if subject_area is not None and subject_area != "all":
            stmt = stmt.where(func.lower(Topic.subject_area) == subject_area.lower())
        if grade is not None:
            stmt = stmt.where(Topic.grade == grade)

        stmt = stmt.order_by(Topic.grade, Topic.name)
        return list(self.db.execute(stmt).scalars().all())

    def get_or_create(
        self,
        name: str,
        subject_area: str = "general",
        grade: int = 10,
        subject_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
    ) -> Topic:
        slug = slugify(name)
        topic = self.get_by_slug(slug)
        if topic:
            return topic

        topic = Topic(
            name=name.strip(),
            slug=slug,
            subject_id=subject_id,
            subject_area=subject_area.lower().strip(),
            grade=grade,
            description=description,
        )
        self.db.add(topic)
        self.db.commit()
        self.db.refresh(topic)
        return topic
