import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select
from jose import jwt, JWTError
import bcrypt
from fastapi import HTTPException, status
from app.config.settings import settings
from app.models.user import User, RefreshToken
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse,
    Token, TokenRefreshResponse,
)

ACCESS_TOKEN_EXPIRE_MINUTES = 30           # 30 minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7              # 7 days

class UserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = UserRepository(db)

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    def create_access_token(self, user: User) -> Tuple[str, int]:
        """Creates a short-lived access token with user role and profile claims."""
        expire_seconds = ACCESS_TOKEN_EXPIRE_MINUTES * 60
        expire = datetime.utcnow() + timedelta(seconds=expire_seconds)
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin,
            "grade": user.grade,
            "token_type": "access",
            "exp": expire,
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return token, expire_seconds

    def create_refresh_token(self, user: User) -> Tuple[str, RefreshToken]:
        """Creates a long-lived refresh token and persists it in PostgreSQL."""
        expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        jti = str(uuid.uuid4())
        payload = {
            "sub": str(user.id),
            "jti": jti,
            "token_type": "refresh",
            "exp": expires_at,
        }
        token_str = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

        db_token = RefreshToken(
            user_id=user.id,
            token=token_str,
            expires_at=expires_at,
            is_revoked=False,
        )
        self.db.add(db_token)
        self.db.commit()
        self.db.refresh(db_token)
        return token_str, db_token

    def issue_token_pair(self, user: User) -> Token:
        """Issues both an Access Token and a persistent Refresh Token."""
        access_token, expires_in = self.create_access_token(user)
        refresh_token, _ = self.create_refresh_token(user)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserResponse.model_validate(user),
        )

    def register(self, user_in: UserCreate, is_admin: bool = False) -> Token:
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
        if is_admin:
            user.is_admin = True
            self.db.commit()
            self.db.refresh(user)

        return self.issue_token_pair(user)

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
                detail="Inactive user account. Please contact administrator.",
            )

        return self.issue_token_pair(user)

    def authenticate_google_user(
        self,
        token_str: str,
        grade: int = 11,
        target_exam: str = "GCE O/L",
    ) -> Token:
        """
        Verifies a Google OAuth ID Token (JWT) sent from the frontend popup,
        and logs in or automatically provisions the student in PostgreSQL.
        """
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        try:
            # Cryptographically verify the Google token signature and audience
            id_info = id_token.verify_oauth2_token(
                token_str,
                google_requests.Request(),
                settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None,
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Google authentication failed: {str(e)}",
            )

        email = id_info.get("email")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google account did not return a valid email address.",
            )

        full_name = id_info.get("name") or id_info.get("given_name") or email.split("@")[0]

        # Find existing user or automatically create account
        user = self.repo.get_by_email(email)
        if not user:
            random_password = self.hash_password(str(uuid.uuid4()))
            user = self.repo.create(
                email=email,
                hashed_password=random_password,
                full_name=full_name,
                grade=grade,
                target_exam=target_exam,
            )
        elif full_name and not user.full_name:
            user.full_name = full_name
            self.db.commit()
            self.db.refresh(user)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is deactivated.",
            )

        return self.issue_token_pair(user)

    def refresh_access_token(self, refresh_token_str: str) -> TokenRefreshResponse:
        """Validates a refresh token and issues a fresh access token."""
        try:
            payload = jwt.decode(refresh_token_str, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("token_type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type. Expected refresh token.",
                )
            user_id_str: str = payload.get("sub")
            if not user_id_str:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token payload.",
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token is expired or malformed. Please log in again.",
            )

        # Check DB record for revocation and expiration
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.token == refresh_token_str)
            .where(RefreshToken.is_revoked == False)
            .where(RefreshToken.expires_at > datetime.utcnow())
        )
        token_record = self.db.execute(stmt).scalar_one_or_none()
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked or expired. Please log in again.",
            )

        user = self.repo.get_by_id(uuid.UUID(user_id_str))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is invalid or deactivated.",
            )

        new_access_token, expires_in = self.create_access_token(user)

        return TokenRefreshResponse(
            access_token=new_access_token,
            refresh_token=refresh_token_str,
            token_type="bearer",
            expires_in=expires_in,
        )

    def revoke_refresh_token(self, refresh_token_str: str) -> bool:
        """Revokes a refresh token on logout."""
        stmt = select(RefreshToken).where(RefreshToken.token == refresh_token_str)
        token_record = self.db.execute(stmt).scalar_one_or_none()
        if token_record:
            token_record.is_revoked = True
            self.db.commit()
            return True
        return False

    def revoke_all_user_tokens(self, user_id: uuid.UUID) -> int:
        """Revokes all active refresh tokens for a user (e.g. security reset)."""
        stmt = (
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.is_revoked == False)
        )
        records = list(self.db.execute(stmt).scalars().all())
        for r in records:
            r.is_revoked = True
        self.db.commit()
        return len(records)

    def get_current_user_by_token(self, token: str) -> User:
        """Validates an access token and returns the active user."""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("token_type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type. Expected access token.",
                )
            user_id: str = payload.get("sub")
            if user_id is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication credentials.",
                )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token is expired or invalid.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = self.repo.get_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or disabled.",
            )
        return user

    def seed_admin_user(
        self,
        email: str = "admin@paperwise.lk",
        password: str = "Admin@12345",
        full_name: str = "System Administrator",
    ) -> User:
        """Seeds an initial administrator account if one does not exist."""
        existing = self.repo.get_by_email(email)
        if existing:
            if not existing.is_admin:
                existing.is_admin = True
                self.db.commit()
                self.db.refresh(existing)
            return existing

        hashed_pwd = self.hash_password(password)
        admin = User(
            email=email.lower().strip(),
            hashed_password=hashed_pwd,
            full_name=full_name,
            grade=11,
            target_exam="GCE O/L",
            is_active=True,
            is_admin=True,
        )
        self.db.add(admin)
        self.db.commit()
        self.db.refresh(admin)
        return admin
