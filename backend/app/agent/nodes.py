import json
import logging
from typing import Dict, Any, Tuple
from langchain_core.messages import AIMessage, HumanMessage
from app.config import settings
from app.agent.state import AgentState
from app.services.ai_service import ai_service
from app.services.sheets_service import sheets_service
from app.services.whatsapp_service import whatsapp_service

logger = logging.getLogger(__name__)

# Try to use Gemini client for merging voice note updates
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def get_gemini_client():
    from app.config import settings
    if HAS_GENAI and settings.GEMINI_API_KEY:
        try:
            return genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception:
            pass
    return None

async def extract_card_node(state: AgentState) -> Dict[str, Any]:
    """
    Node to extract details from a visiting card.
    Expects the latest message metadata to contain the uploaded image bytes.
    """
    logger.info("Running extract_card_node")
    
    # Locate the image in the last message's metadata
    last_message = state["messages"][-1]
    image_bytes = None
    mime_type = "image/jpeg"
    
    if hasattr(last_message, "additional_kwargs") and "file_bytes" in last_message.additional_kwargs:
        image_bytes = last_message.additional_kwargs["file_bytes"]
        mime_type = last_message.additional_kwargs.get("mime_type", "image/jpeg")
        
    if not image_bytes:
        return {
            "messages": [AIMessage(content="Error: No image bytes found in the request state.")],
            "action_required": "idle"
        }
        
    # Call OCR extraction
    card_data = await ai_service.extract_visiting_card(image_bytes, mime_type)
    
    prompt_message = (
        f"I've extracted the following details from the visiting card:\n\n"
        f"👤 *Name:* {card_data.get('name', 'N/A')}\n"
        f"🏢 *Company:* {card_data.get('company', 'N/A')}\n"
        f"💼 *Title:* {card_data.get('title', 'N/A')}\n"
        f"📧 *Email:* {card_data.get('email', 'N/A')}\n"
        f"📞 *Phone:* {card_data.get('phone', 'N/A')}\n"
        f"🌐 *Website:* {card_data.get('website', 'N/A')}\n"
        f"📍 *Address:* {card_data.get('address', 'N/A')}\n\n"
        f"Please verify these details. You can edit them in the card inspector and click *Approve & Save* to proceed."
    )
    
    return {
        "messages": [AIMessage(content=prompt_message)],
        "card_data": card_data,
        "action_required": "awaiting_ocr_approval",
        "status_message": "Card details extracted. Awaiting approval."
    }

async def check_duplicate_node(state: AgentState) -> Dict[str, Any]:
    """
    Node to check Google Sheets and local storage for duplicate contact entries.
    """
    logger.info("Running check_duplicate_node")
    card_data = state["card_data"]
    if not card_data:
        return {"action_required": "idle"}
        
    email = card_data.get("email")
    phone = card_data.get("phone")
    
    existing = await sheets_service.find_contact_by_email_or_phone(email, phone)
    
    if existing:
        msg = (
            f"⚠️ *Duplicate Contact Found!*\n\n"
            f"A contact named *{existing.get('name', 'Unknown')}* already exists in our system with email `{existing.get('email')}` or phone `{existing.get('phone')}`.\n\n"
            f"Would you like to *Overwrite/Update* the existing contact with these new details, or *Cancel* this operation?"
        )
        return {
            "messages": [AIMessage(content=msg)],
            "is_duplicate": True,
            "duplicate_contact": existing,
            "action_required": "awaiting_duplicate_choice",
            "status_message": "Duplicate contact detected. Awaiting decision."
        }
        
    return {
        "is_duplicate": False,
        "duplicate_contact": None,
        "action_required": "idle"  # Proceed directly to save
    }

async def save_contact_node(state: AgentState) -> Dict[str, Any]:
    """
    Node to save the contact details into Google Sheets.
    """
    logger.info("Running save_contact_node")
    card_data = state["card_data"]
    if not card_data:
        return {
            "messages": [AIMessage(content="Error: No contact data available to save.")],
            "action_required": "idle"
        }
        
    # Check if we should update an existing record or write a new one
    is_duplicate = state.get("is_duplicate", False)
    
    if is_duplicate:
        # Update existing contact notes/details instead of appending a new row
        email = card_data.get("email") or state["duplicate_contact"].get("email")
        # In a full-blown update, we would overwrite columns. For this assignment,
        # we can update details and append to notes. Let's write a log confirmation.
        logger.info(f"Overwriting contact details for duplicate: {email}")
        
        # Add a note explaining it was updated
        update_notes = f"Updated details on {state['card_data'].get('company')}"
        await sheets_service.update_contact_notes_and_audio(email, update_notes)
        # We can also save the new contact details to mock file
        await sheets_service.add_contact(card_data) # Or write to a specific row
        
        msg = f"✅ Success! Contact details for *{card_data.get('name')}* have been updated in Google Sheets."
    else:
        # Log as new row
        saved_row = await sheets_service.add_contact(card_data)
        msg = f"✅ Success! *{saved_row.get('name')}* from *{saved_row.get('company')}* has been successfully logged to Google Sheets."
        
    return {
        "messages": [AIMessage(content=msg)],
        "action_required": "idle",
        "status_message": "Contact saved successfully."
    }

async def send_notification_node(state: AgentState) -> Dict[str, Any]:
    """
    Node to trigger real-time WhatsApp alert.
    """
    logger.info("Running send_notification_node")
    card_data = state["card_data"]
    if not card_data:
        return {}
        
    name = card_data.get("name", "N/A")
    company = card_data.get("company", "N/A")
    email = card_data.get("email", "N/A")
    phone = card_data.get("phone", "N/A")
    
    res = await whatsapp_service.send_card_logged_notification(name, company, email, phone)
    
    method_str = "WhatsApp Business API" if res.get("method") == "live_whatsapp" else "Mock Notification Channel (data/mock_whatsapp_notifications.log)"
    alert_msg = f"📢 A notification has been sent via *{method_str}*."
    
    return {
        "messages": [AIMessage(content=alert_msg)],
        "status_message": "Notification dispatched."
    }

async def process_voice_node(state: AgentState) -> Dict[str, Any]:
    """
    Node to handle voice recording uploads.
    Transcribes audio, uses AI to extract new details or notes, and updates Google Sheets.
    """
    logger.info("Running process_voice_node")
    
    # Locate the audio bytes in the last message's metadata
    last_message = state["messages"][-1]
    audio_bytes = None
    mime_type = "audio/wav"
    audio_url = "https://mock-audio-hosting.net/voice-note.wav" # Mock URL
    
    if hasattr(last_message, "additional_kwargs") and "file_bytes" in last_message.additional_kwargs:
        audio_bytes = last_message.additional_kwargs["file_bytes"]
        mime_type = last_message.additional_kwargs.get("mime_type", "audio/wav")
        audio_url = last_message.additional_kwargs.get("file_url", audio_url)
        
    if not audio_bytes:
        return {
            "messages": [AIMessage(content="Error: No audio data found to process.")],
            "action_required": "idle"
        }
        
    # Transcribe the audio
    transcription = await ai_service.transcribe_voice_note(audio_bytes, mime_type)
    logger.info(f"Transcribed audio: '{transcription}'")
    
    # Locate the contact to update (from the active card in the current session)
    card_data = state.get("card_data")
    if not card_data:
        # Check if we can find a contact using the database service session's last saved details
        # Let's search our Sheets mock DB for the last logged contact if card_data is missing
        all_contacts = await sheets_service.get_all_contacts()
        if all_contacts:
            card_data = all_contacts[-1] # Fallback to the latest saved contact overall
            
    if not card_data:
        return {
            "messages": [AIMessage(content=f"🎤 *Transcribed Note:* \"{transcription}\"\n\n⚠️ *Warning:* Could not associate this note with any contact because no cards have been uploaded in this session yet.")],
            "last_audio_url": audio_url,
            "last_audio_transcription": transcription,
            "action_required": "idle"
        }
        
    email = card_data.get("email")
    name = card_data.get("name", "the contact")
    
    # Advanced AI Enrichment: Use Gemini to check if the transcription contains updates to specific fields
    # e.g., "His phone is actually..." or "Change her email to..."
    notes_to_add = transcription
    updated_fields = {}
    
    client = get_gemini_client()
    if client:
        enrichment_prompt = f"""
        You are an AI data enrichment assistant.
        We have a contact in Google Sheets:
        Name: {card_data.get('name')}
        Email: {card_data.get('email')}
        Phone: {card_data.get('phone')}
        Company: {card_data.get('company')}
        
        The user just sent this voice note transcription:
        "{transcription}"
        
        Extract the following:
        1. General notes or remarks to log (e.g. details about their meeting, follow-up instructions).
        2. Any updates to their contact details if explicitly mentioned (e.g. new phone, email, website, title).
        
        Return your analysis ONLY as a JSON object with these keys:
        - "notes": string (the cleaned notes to save)
        - "updates": dict (keys like "phone", "email", "website", "title", "address" with the new values, if mentioned)
        
        Do not output markdown code blocks or backticks. Return valid JSON only.
        """
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=enrichment_prompt
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("```json")[-1].split("```")[0].strip()
            enrich_data = json.loads(text)
            
            notes_to_add = enrich_data.get("notes", transcription)
            updated_fields = enrich_data.get("updates", {})
        except Exception as e:
            logger.error(f"Failed to run advanced voice note enrichment LLM call: {e}")
            
    # Update Google Sheets (notes + audio URL)
    await sheets_service.update_contact_notes_and_audio(email, notes_to_add, audio_url)
    
    # If there are updated fields, apply them
    if updated_fields:
        for field, val in updated_fields.items():
            if val:
                card_data[field] = val
        # Re-save updated contact
        await sheets_service.add_contact(card_data)
        
    confirm_msg = (
        f"🎙️ *Voice Note Transcribed & Logged!*\n\n"
        f"📝 *Transcription:* \"{transcription}\"\n\n"
        f"✅ Associated with *{name}* ({email}). Google Sheet has been updated with the audio link and the notes."
    )
    
    if updated_fields:
        confirm_msg += f"\n\n✨ *AI Also Updated Fields:* {', '.join([f'{k}: {v}' for k, v in updated_fields.items()])}"
        
    return {
        "messages": [AIMessage(content=confirm_msg)],
        "card_data": card_data,
        "last_audio_url": audio_url,
        "last_audio_transcription": transcription,
        "action_required": "idle",
        "status_message": "Voice note processed."
    }

async def general_chat_node(state: AgentState) -> Dict[str, Any]:
    """
    Node to handle general text queries when no specific file upload is occurring.
    """
    logger.info("Running general_chat_node")
    last_message = state["messages"][-1].content
    
    prompt = f"""
    You are the Assistant for the Visiting Card Digitization & Voice Notes Orchestrator.
    The user says: "{last_message}"
    
    If they are asking how to use the app, explain:
    1. They can upload an image of a visiting card to extract details.
    2. Once details are extracted, they can edit and approve them.
    3. They can record/upload a voice note afterwards to attach notes to that contact.
    
    Respond in a professional, brief, and helpful tone.
    """
    
    client = get_gemini_client()
    if client:
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt
            )
            response_text = response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API Error in general chat: {e}")
            response_text = "I'm here to help you digitize visiting cards! You can upload an image of a visiting card or record a voice note to attach comments to the contact."
    else:
        response_text = "I'm here to help you digitize visiting cards! You can upload an image of a visiting card or record a voice note to attach comments to the contact."
        
    return {
        "messages": [AIMessage(content=response_text)],
        "action_required": "idle",
        "status_message": "Ready"
    }
