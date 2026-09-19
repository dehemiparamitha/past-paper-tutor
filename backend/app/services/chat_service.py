import uuid
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatSessionResponse, ChatSessionCreate,
    ChatMessageResponse, ChatMessageCreate,
)
from app.services.rag_service import ask_question

class ChatService:
    def __init__(self, db: Session):
        self.db = db

    def list_sessions(self, user_id: Optional[uuid.UUID] = None, limit: int = 50) -> List[ChatSessionResponse]:
        stmt = select(ChatSession)
        if user_id is not None:
            stmt = stmt.where(ChatSession.user_id == user_id)
        stmt = stmt.order_by(desc(ChatSession.updated_at)).limit(limit)
        sessions = list(self.db.execute(stmt).scalars().all())
        return [ChatSessionResponse.model_validate(s) for s in sessions]

    def get_session(self, session_id: uuid.UUID) -> Optional[ChatSessionResponse]:
        session = self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        ).scalar_one_or_none()
        if not session:
            return None
        return ChatSessionResponse.model_validate(session)

    def create_session(
        self, session_in: ChatSessionCreate, user_id: Optional[uuid.UUID] = None
    ) -> ChatSessionResponse:
        session = ChatSession(
            title=session_in.title or "New Conversation",
            user_id=user_id,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return ChatSessionResponse.model_validate(session)

    def ask_in_session(
        self,
        session_id: uuid.UUID,
        question: str,
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        # 1. Ensure session exists
        session = self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id)
        ).scalar_one_or_none()

        if not session:
            session = ChatSession(
                id=session_id,
                title=question[:40] + ("..." if len(question) > 40 else ""),
                user_id=user_id,
            )
            self.db.add(session)
            self.db.flush()
        elif session.title == "New Conversation":
            session.title = question[:40] + ("..." if len(question) > 40 else "")

        # 2. Record User Message
        user_msg = ChatMessage(
            session_id=session.id,
            sender="user",
            content=question,
        )
        self.db.add(user_msg)
        self.db.flush()

        # 3. Generate AI response via RAG pipeline
        rag_answer = ask_question(question)
        answer_text = rag_answer if isinstance(rag_answer, str) else str(rag_answer)

        # 4. Record Assistant Message
        bot_msg = ChatMessage(
            session_id=session.id,
            sender="assistant",
            content=answer_text,
            sources=[],
        )
        self.db.add(bot_msg)
        self.db.commit()
        self.db.refresh(bot_msg)

        return {
            "session_id": str(session.id),
            "user_message_id": str(user_msg.id),
            "assistant_message_id": str(bot_msg.id),
            "answer": bot_msg.content,
            "sources": bot_msg.sources or [],
            "title": session.title,
        }
