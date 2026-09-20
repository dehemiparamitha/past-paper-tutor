from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.deps import get_current_user, get_current_admin
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserLogin, UserResponse,
    Token, TokenRefreshRequest, TokenRefreshResponse, LogoutRequest,
    GoogleLoginRequest,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new student account.
    Returns both a short-lived access token and a long-lived refresh token.
    """
    service = UserService(db)
    return service.register(user_in)

@router.post("/login", response_model=Token)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    """
    Log in with email and password.
    Returns both an access token (for API requests) and a refresh token.
    """
    service = UserService(db)
    return service.authenticate(login_in)

@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(req: TokenRefreshRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid, unrevoked refresh token for a fresh access token.
    """
    service = UserService(db)
    return service.refresh_access_token(req.refresh_token)

@router.post("/logout")
def logout(req: LogoutRequest, db: Session = Depends(get_db)):
    """
    Revoke a refresh token on user logout so it cannot be used again.
    """
    service = UserService(db)
    revoked = service.revoke_refresh_token(req.refresh_token)
    return {"success": True, "message": "Logged out successfully" if revoked else "Token already inactive"}

@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """
    Retrieve profile and role information of the currently authenticated user.
    """
    return UserResponse.model_validate(current_user)

@router.post("/google", response_model=Token)
def google_login(req: GoogleLoginRequest, db: Session = Depends(get_db)):
    """
    Log in or register seamlessly using a Google OAuth ID Token (JWT).
    Returns both an access token and a refresh token.
    """
    service = UserService(db)
    return service.authenticate_google_user(req.id_token, req.grade or 11, req.target_exam or "GCE O/L")

@router.post("/seed-admin", response_model=UserResponse)
def seed_admin(db: Session = Depends(get_db)):
    """
    Helper endpoint to ensure a default administrator account exists.
    """
    service = UserService(db)
    admin = service.seed_admin_user()
    return UserResponse.model_validate(admin)

