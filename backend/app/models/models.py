from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

class ChatRequest(BaseModel):
    text: str = Field(..., description="Message text sent by the user")
    session_id: str = Field(..., description="Unique conversation session ID")

class ApproveCardRequest(BaseModel):
    session_id: str = Field(..., description="Unique conversation session ID")
    card_data: Dict[str, Any] = Field(..., description="Modified or verified visiting card fields")

class CreateSessionRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="Optional name for the session")

class SessionResponse(BaseModel):
    id: str
    name: str
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    id: Any
    session_id: str
    sender: str
    content: str
    msg_type: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str

class ContactDetail(BaseModel):
    name: str
    phone: str
    email: str
    company: str
    title: Optional[str] = None
    website: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    audio_url: Optional[str] = None
