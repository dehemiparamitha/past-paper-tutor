import os
from pydantic_settings import BaseSettings
from typing import List, Union

class Settings(BaseSettings):
    PROJECT_NAME: str = "Past Paper Tutor API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"

    # PostgreSQL Database URL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/past_paper_db"
    )

    # Chroma Vector Store
    CHROMA_PERSIST_DIRECTORY: str = os.getenv("CHROMA_PERSIST_DIRECTORY", "chroma_db")

    # Google Gemini AI Key
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")

    # Google OAuth 2.0 Credentials
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # Security & JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "temporary-super-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
