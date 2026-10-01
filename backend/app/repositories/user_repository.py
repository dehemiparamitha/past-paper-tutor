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
        language: Optional[str] = "English",
        school: Optional[str] = None,
        district: Optional[str] = "Colombo",
        study_goal: Optional[str] = "Finals prep",
        weekly_hours: Optional[str] = "5 hours a week",
        study_time: Optional[str] = "Weekdays at 7 PM",
        confidence_level: Optional[str] = "Finding my footing",
        onboarding_completed: bool = False,
    ) -> User:
        user = User(
            email=email.lower().strip(),
            hashed_password=hashed_password,
            full_name=full_name,
            grade=grade,
            target_exam=target_exam,
            language=language,
            school=school,
            district=district,
            study_goal=study_goal,
            weekly_hours=weekly_hours,
            study_time=study_time,
            confidence_level=confidence_level,
            onboarding_completed=onboarding_completed,
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
        language: Optional[str] = None,
        school: Optional[str] = None,
        district: Optional[str] = None,
        study_goal: Optional[str] = None,
        weekly_hours: Optional[str] = None,
        study_time: Optional[str] = None,
        confidence_level: Optional[str] = None,
        onboarding_completed: Optional[bool] = None,
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
        if language is not None:
            user.language = language
        if school is not None:
            user.school = school
        if district is not None:
            user.district = district
        if study_goal is not None:
            user.study_goal = study_goal
        if weekly_hours is not None:
            user.weekly_hours = weekly_hours
        if study_time is not None:
            user.study_time = study_time
        if confidence_level is not None:
            user.confidence_level = confidence_level
        if onboarding_completed is not None:
            user.onboarding_completed = onboarding_completed
        self.db.commit()
        self.db.refresh(user)
        return user
