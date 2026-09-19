import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel

class ChatMessageBase(BaseModel):
    sender: str  # 'user' | 'assistant'
    content: str
    sources: Optional[List[dict[str, Any]]] = None

class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(ChatMessageBase):
    id: uuid.UUID
    session_id: uuid.UUID
    tokens_used: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionBase(BaseModel):
    title: str = "New Conversation"

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class ChatSessionResponse(ChatSessionBase):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True
