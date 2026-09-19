from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config.settings import settings
from app.api.routes.auth import router as auth_router
from app.api.routes.documents import router as documents_router
from app.api.routes.questions import router as questions_router
from app.api.routes.chat import router as chat_router
from app.api.routes.practice import router as practice_router
from app.database.session import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Intelligent AI Past Paper Tutor API with PostgreSQL Document Modeling and Chroma Semantic Retrieval",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    """Attempt database table initialization on startup if tables don't already exist."""
    try:
        init_db()
        print("✓ Database initialized successfully.")
    except Exception as e:
        print(f"! Database initialization note: {e}")

@app.get("/")
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "online",
        "docs_url": "/docs",
    }

# Register all modular routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(questions_router)
app.include_router(chat_router)
app.include_router(practice_router)