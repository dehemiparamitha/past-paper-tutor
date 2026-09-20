import uuid
from typing import Optional
from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.user import User
from app.services.user_service import UserService

def get_current_user(
    authorization: Optional[str] = Header(None, description="Bearer <access_token>"),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency that extracts and validates the Bearer access token,
    returning the authenticated user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide 'Authorization: Bearer <access_token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split(" ")[1]
    service = UserService(db)
    return service.get_current_user_by_token(token)

def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    FastAPI dependency that guarantees the authenticated user has admin privileges.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to administrators only.",
        )
    return current_user

def get_optional_user(
    authorization: Optional[str] = Header(None, description="Optional Bearer <access_token>"),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    FastAPI dependency for endpoints that support both authenticated users and guest access.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        service = UserService(db)
        return service.get_current_user_by_token(token)
    except HTTPException:
        return None
