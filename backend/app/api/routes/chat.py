import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.schemas.chat import (
    ChatSessionResponse, ChatSessionCreate,
    ChatMessageResponse, ChatMessageCreate,
)
from app.services.chat_service import ChatService
from app.services.rag_service import (
    ask_question,
    find_similar_questions,
    get_topic_frequency,
    get_topic_trends,
    calculate_important_topics,
)

router = APIRouter(tags=["Chat & Past Paper RAG"])

# --- Legacy & Direct RAG Chat Endpoints (100% Backward Compatible) ---

@router.post("/chat")
def chat(request: dict):
    question = request.get("question", "")
    result = ask_question(question)
    return result


@router.get("/api/questions/similar")
def get_similar_questions(
    query: str = Query(..., min_length=1),
    start_year: Optional[int] = Query(None, ge=1900, le=2100),
    end_year: Optional[int] = Query(None, ge=1900, le=2100),
    year: Optional[int] = Query(None, ge=1900, le=2100),
    question_type: Optional[str] = Query(None),
):
    return {
        "results": find_similar_questions(
            query=query,
            start_year=start_year,
            end_year=end_year,
            year=year,
            question_type=question_type,
        )
    }

@router.get("/api/topics/frequency")
def get_topics_frequency(
    year: Optional[int] = Query(None, ge=1900, le=2100),
    start_year: Optional[int] = Query(None, ge=1900, le=2100),
    end_year: Optional[int] = Query(None, ge=1900, le=2100),
):
    frequencies = get_topic_frequency(
        year=year,
        start_year=start_year,
        end_year=end_year,
    )
    return {
        "total_topics": len(frequencies),
        "frequencies": frequencies,
    }

@router.get("/api/topics/trends")
def get_topics_trends(topic: Optional[str] = Query(None)):
    trends = get_topic_trends(topic=topic)
    return {
        "total_topics": len(trends),
        "trends": trends,
    }

@router.get("/api/topics/important")
def get_important_topics():
    topics = calculate_important_topics()
    return {
        "total_analyzed": len(topics),
        "high_priority_count": len([t for t in topics if t["tier"] == "High"]),
        "topics": topics,
    }

# --- Database-Persisted Chat Session Endpoints ---

@router.get("/chat/sessions", response_model=List[ChatSessionResponse])
def list_chat_sessions(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List chat sessions with persistent database history."""
    service = ChatService(db)
    return service.list_sessions(limit=limit)

@router.post("/chat/sessions", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
def create_chat_session(
    session_in: ChatSessionCreate,
    db: Session = Depends(get_db),
):
    """Create a new chat conversation session."""
    service = ChatService(db)
    return service.create_session(session_in)

@router.get("/chat/sessions/{session_id}", response_model=ChatSessionResponse)
def get_chat_session(
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Retrieve conversation messages for a specific session."""
    service = ChatService(db)
    session = service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat session {session_id} not found",
        )
    return session

@router.post("/chat/sessions/{session_id}/message")
def send_message_to_session(
    session_id: uuid.UUID,
    message_in: ChatMessageCreate,
    db: Session = Depends(get_db),
):
    """Send a question into a session, saving messages and receiving RAG answer with citations."""
    service = ChatService(db)
    return service.ask_in_session(
        session_id=session_id,
        question=message_in.content,
    )