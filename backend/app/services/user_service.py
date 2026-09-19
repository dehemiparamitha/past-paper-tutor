import uuid
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from jose import jwt, JWTError
import bcrypt
from fastapi import HTTPException, status
from app.config.settings import settings
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def register(self, user_in: UserCreate) -> Token:
        existing = self.repo.get_by_email(user_in.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )

        hashed_pwd = self.hash_password(user_in.password)
        user = self.repo.create(
            email=user_in.email,
            hashed_password=hashed_pwd,
            full_name=user_in.full_name,
            grade=user_in.grade,
            target_exam=user_in.target_exam,
        )

        access_token = self.create_access_token(data={"sub": str(user.id), "email": user.email})
        return Token(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )

    def authenticate(self, login_in: UserLogin) -> Token:
        user = self.repo.get_by_email(login_in.email)
        if not user or not self.verify_password(login_in.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inactive user account.",
            )

        access_token = self.create_access_token(data={"sub": str(user.id), "email": user.email})
        return Token(
            access_token=access_token,
            user=UserResponse.model_validate(user),
        )

    def get_current_user_by_token(self, token: str) -> User:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials",
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        user = self.repo.get_by_id(uuid.UUID(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user
