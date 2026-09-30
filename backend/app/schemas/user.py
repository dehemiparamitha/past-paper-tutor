import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    grade: int = 11
    target_exam: str = "GCE O/L"
    language: Optional[str] = "English"
    school: Optional[str] = None
    district: Optional[str] = "Colombo"
    study_goal: Optional[str] = "Finals prep"
    weekly_hours: Optional[str] = "5 hours a week"
    study_time: Optional[str] = "Weekdays at 7 PM"
    confidence_level: Optional[str] = "Finding my footing"
    onboarding_completed: bool = False

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    grade: Optional[int] = None
    target_exam: Optional[str] = None
    language: Optional[str] = None
    school: Optional[str] = None
    district: Optional[str] = None
    study_goal: Optional[str] = None
    weekly_hours: Optional[str] = None
    study_time: Optional[str] = None
    confidence_level: Optional[str] = None
    onboarding_completed: Optional[bool] = None

class OnboardingRequest(BaseModel):
    full_name: Optional[str] = None
    language: Optional[str] = "English"
    school: Optional[str] = None
    district: Optional[str] = "Colombo"
    target_exam: Optional[str] = "GCE O/L"
    grade: Optional[int] = 11
    study_goal: Optional[str] = "Finals prep"
    weekly_hours: Optional[str] = "5 hours a week"
    study_time: Optional[str] = "Weekdays at 7 PM"
    confidence_level: Optional[str] = "Finding my footing"
    onboarding_completed: bool = True

class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # Access token lifespan in seconds (e.g. 1800 for 30 mins)
    user: UserResponse

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int

class LogoutRequest(BaseModel):
    refresh_token: str

class GoogleLoginRequest(BaseModel):
    id_token: str
    grade: Optional[int] = 11
    target_exam: Optional[str] = "GCE O/L"

