import uuid
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        return self.db.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.execute(
            select(User).where(User.email == email.lower().strip())
        ).scalar_one_or_none()

    def create(
        self,
        email: str,
        hashed_password: str,
        full_name: Optional[str] = None,
        grade: int = 11,
        target_exam: str = "GCE O/L",
    ) -> User:
        user = User(
            email=email.lower().strip(),
            hashed_password=hashed_password,
            full_name=full_name,
            grade=grade,
            target_exam=target_exam,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_profile(
        self,
        user_id: uuid.UUID,
        full_name: Optional[str] = None,
        grade: Optional[int] = None,
        target_exam: Optional[str] = None,
    ) -> Optional[User]:
        user = self.get_by_id(user_id)
        if not user:
            return None
        if full_name is not None:
            user.full_name = full_name
        if grade is not None:
            user.grade = grade
        if target_exam is not None:
            user.target_exam = target_exam
        self.db.commit()
        self.db.refresh(user)
        return user
