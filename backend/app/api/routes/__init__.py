from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.questions import router as questions_router
from app.api.routes.chat import router as chat_router
from app.api.routes.practice import router as practice_router

__all__ = [
    "auth_router",
    "documents_router",
    "questions_router",
    "chat_router",
    "practice_router",
]
