from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # LangGraph standard message history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # Session & metadata
    session_id: str
    
    # Active data model
    card_data: Optional[Dict[str, Any]]
    
    # Deduplication state
    is_duplicate: bool
    duplicate_contact: Optional[Dict[str, Any]]
    
    # Voice notes state
    last_audio_url: Optional[str]
    last_audio_transcription: Optional[str]
    
    # Agent status control
    action_required: Optional[str]  # "awaiting_ocr_approval", "awaiting_duplicate_choice", "idle"
    status_message: Optional[str]   # "Extracting...", "Duplicate check...", etc.
