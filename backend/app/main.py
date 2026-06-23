import os
import uuid
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage, AIMessage

from app.config import settings
from app.models.models import ChatRequest, ApproveCardRequest, CreateSessionRequest, SessionResponse, MessageResponse
from app.services.db_service import db_service
from app.services.sheets_service import sheets_service
from app.agent.graph import agent_graph

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Visiting Card Digitization & Voice Notes Orchestrator API")

# Configure CORS for local React dev server and Render deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure data and upload directories exist
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)

# Mount the static data directory so uploaded files and logs are downloadable/viewable
app.mount("/static", StaticFiles(directory=DATA_DIR), name="static")

# Helper serialization functions
def serialize_messages(messages: List[Any]) -> List[Dict[str, Any]]:
    serialized = []
    for msg in messages:
        kwargs = getattr(msg, "additional_kwargs", {})
        kwargs_clean = {k: v for k, v in kwargs.items() if k != "file_bytes"}
        if isinstance(msg, HumanMessage):
            serialized.append({
                "type": "human",
                "content": msg.content,
                "additional_kwargs": kwargs_clean
            })
        elif isinstance(msg, AIMessage):
            serialized.append({
                "type": "ai",
                "content": msg.content,
                "additional_kwargs": kwargs_clean
            })
    return serialized

def deserialize_messages(serialized: List[Dict[str, Any]]) -> List[Any]:
    messages = []
    for msg in serialized:
        if msg["type"] == "human":
            messages.append(HumanMessage(
                content=msg["content"],
                additional_kwargs=msg.get("additional_kwargs", {})
            ))
        elif msg["type"] == "ai":
            messages.append(AIMessage(
                content=msg["content"],
                additional_kwargs=msg.get("additional_kwargs", {})
            ))
    return messages

async def run_agent_and_persist(session_id: str, new_user_message: HumanMessage) -> Dict[str, Any]:
    """
    Load agent state, append new message, run LangGraph, save messages, and persist state.
    """
    # Load state
    state_dict = await db_service.get_agent_state(session_id)
    if not state_dict:
        state_dict = {
            "messages": [],
            "session_id": session_id,
            "card_data": None,
            "is_duplicate": False,
            "duplicate_contact": None,
            "last_audio_url": None,
            "last_audio_transcription": None,
            "action_required": "idle",
            "status_message": "Ready"
        }
        
    # Reconstruct messages from db format to LangChain objects
    messages_list = deserialize_messages(state_dict.get("messages", []))
    
    # Add new user message
    messages_list.append(new_user_message)
    state_dict["messages"] = messages_list
    
    # Save user message to chat history DB
    msg_type = "text"
    metadata = {}
    if hasattr(new_user_message, "additional_kwargs"):
        metadata = {k: v for k, v in new_user_message.additional_kwargs.items() if k != "file_bytes"}
        if "file_type" in new_user_message.additional_kwargs:
            msg_type = new_user_message.additional_kwargs["file_type"]
            
    await db_service.add_message(
        session_id=session_id,
        sender="user",
        content=new_user_message.content,
        msg_type=msg_type,
        metadata=metadata
    )
    
    # Run the graph
    output_state = await agent_graph.ainvoke(state_dict)
    
    # Find new AI messages added by the graph
    input_msg_count = len(messages_list)
    new_messages = output_state["messages"][input_msg_count:]
    
    # Save new AI messages to chat history DB
    for msg in new_messages:
        await db_service.add_message(
            session_id=session_id,
            sender="agent",
            content=msg.content,
            msg_type="text",
            metadata=getattr(msg, "additional_kwargs", {})
        )
        
    # Serialize messages for state persistence
    output_state["messages"] = serialize_messages(output_state["messages"])
    
    # Save updated agent state to DB
    await db_service.save_agent_state(session_id, output_state)
    
    return {
        "status": "success",
        "action_required": output_state.get("action_required", "idle"),
        "status_message": output_state.get("status_message", "Ready"),
        "card_data": output_state.get("card_data"),
        "is_duplicate": output_state.get("is_duplicate", False),
        "duplicate_contact": output_state.get("duplicate_contact")
    }

# --- ENDPOINTS ---

@app.get("/")
def read_root():
    return {
        "message": "Visiting Card Digitization & Voice Notes Orchestrator Backend API is running!",
        "version": "1.0",
        "environment": settings.ENVIRONMENT,
        "features": {
            "sheets_configured": settings.is_sheets_configured,
            "whatsapp_configured": settings.is_whatsapp_configured,
            "mongodb_configured": settings.is_mongodb_configured
        }
    }

@app.post("/api/sessions", response_model=SessionResponse)
async def create_session(req: CreateSessionRequest):
    session_id = str(uuid.uuid4())
    name = req.name or f"Session {session_id[:8]}"
    session = await db_service.create_session(session_id, name)
    return session

@app.get("/api/sessions", response_model=List[SessionResponse])
async def get_sessions():
    return await db_service.list_sessions()

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    success = await db_service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": f"Deleted session {session_id}"}

@app.get("/api/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(session_id: str):
    return await db_service.get_messages(session_id)

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Send a normal chat message to the agent.
    """
    user_msg = HumanMessage(content=req.text)
    return await run_agent_and_persist(req.session_id, user_msg)

@app.post("/api/upload-card")
async def upload_card(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a visiting card image. Extracts details via Gemini Vision API.
    """
    # Verify file is an image
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image.")
        
    # Read file and save locally
    file_bytes = await file.read()
    file_ext = os.path.splitext(file.filename)[1] or ".jpg"
    saved_filename = f"card_{uuid.uuid4()}{file_ext}"
    saved_filepath = os.path.join(UPLOADS_DIR, saved_filename)
    
    with open(saved_filepath, "wb") as f:
        f.write(file_bytes)
        
    file_url = f"/static/uploads/{saved_filename}"
    
    # Create user message with image details in metadata
    user_msg = HumanMessage(
        content=f"[Uploaded Visiting Card: {file.filename}]",
        additional_kwargs={
            "file_type": "image",
            "file_bytes": file_bytes,
            "mime_type": file.content_type,
            "file_url": file_url,
            "filename": file.filename
        }
    )
    
    return await run_agent_and_persist(session_id, user_msg)

@app.post("/api/approve-card")
async def approve_card(req: ApproveCardRequest):
    """
    Human-in-the-loop approval: Confirms edited/verified visiting card data.
    """
    # Load current state
    state_dict = await db_service.get_agent_state(req.session_id)
    if not state_dict:
        raise HTTPException(status_code=404, detail="Active session not found")
        
    # Overwrite card data with user-modified/approved data
    state_dict["card_data"] = req.card_data
    state_dict["action_required"] = "idle"  # Clear the block
    
    # Re-save modified state prior to invoking next node
    state_dict["messages"] = serialize_messages(deserialize_messages(state_dict.get("messages", [])))
    await db_service.save_agent_state(req.session_id, state_dict)
    
    # Create the approval human message with special approved metadata
    approved_msg = HumanMessage(
        content="Approved visiting card details",
        additional_kwargs={
            "approved": True
        }
    )
    
    # Run agent graph starting at duplicate checker
    return await run_agent_and_persist(req.session_id, approved_msg)

@app.post("/api/upload-voice")
async def upload_voice(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    """
    Upload a voice note recording. Transcribes audio and updates Sheets.
    """
    if not file.content_type.startswith("audio/"):
        # Allow octet-stream for blobs without specific audio type, typical from browser records
        if "octet-stream" not in file.content_type and "webm" not in file.filename:
            raise HTTPException(status_code=400, detail="Uploaded file must be audio.")
            
    # Read file and save locally
    file_bytes = await file.read()
    file_ext = os.path.splitext(file.filename)[1] or ".wav"
    saved_filename = f"voice_{uuid.uuid4()}{file_ext}"
    saved_filepath = os.path.join(UPLOADS_DIR, saved_filename)
    
    with open(saved_filepath, "wb") as f:
        f.write(file_bytes)
        
    file_url = f"/static/uploads/{saved_filename}"
    
    # Create user message with audio details in metadata
    user_msg = HumanMessage(
        content=f"[Uploaded Voice Note: {file.filename}]",
        additional_kwargs={
            "file_type": "audio",
            "file_bytes": file_bytes,
            "mime_type": file.content_type,
            "file_url": file_url,
            "filename": file.filename
        }
    )
    
    return await run_agent_and_persist(session_id, user_msg)

@app.get("/api/contacts")
async def get_contacts():
    """
    Retrieve all digitized contacts (Google Sheet + local mock mirror).
    """
    return await sheets_service.get_all_contacts()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
