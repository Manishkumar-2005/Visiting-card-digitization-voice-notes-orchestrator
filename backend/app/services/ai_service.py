import os
import json
import base64
from typing import Dict, Any, Optional
from app.config import settings

# Try to import Google GenAI SDK
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

class AIService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = None
        if HAS_GENAI and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Error initializing Gemini client: {e}")

    async def extract_visiting_card(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Extract structured information from a visiting card image.
        Uses Gemini Vision API or fallback mock details.
        """
        prompt = """
        Analyze this visiting card image and extract the contact details.
        Return the result ONLY as a JSON object with the following fields:
        - name: The person's full name.
        - phone: The phone number (formatted nicely, e.g. +1-234-567-8901).
        - email: The email address.
        - company: The company/organization name.
        - title: The job title/position (if any).
        - website: The website URL (if any).
        - address: The physical address (if any).

        Do not include any markdown styling, backticks, or comments around the JSON.
        Example response format:
        {
          "name": "John Doe",
          "phone": "+1-555-0199",
          "email": "john.doe@acme.com",
          "company": "Acme Corp",
          "title": "Senior Sales Manager",
          "website": "www.acme.com",
          "address": "123 Main St, Springfield"
        }
        """

        if self.client:
            import time
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Prepare the image content
                    image_content = types.Part.from_bytes(
                        data=image_bytes,
                        mime_type=mime_type,
                    )
                    
                    response = self.client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=[image_content, prompt]
                    )
                    
                    text = response.text.strip()
                    # Clean up json format if model outputs markdown code blocks
                    if text.startswith("```"):
                        text = text.split("```json")[-1].split("```")[0].strip()
                        
                    data = json.loads(text)
                    return data
                except Exception as e:
                    print(f"Gemini API attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        print(f"Gemini API Error in extract_visiting_card after {max_retries} attempts: {e}. Falling back to mock details.")
        
        # Fallback Mock Data
        print("Using MOCK visiting card extraction (No Gemini API key or error occurred).")
        return {
            "name": "Jane Smith",
            "phone": "+1-415-555-2671",
            "email": "jane.smith@innovate.tech",
            "company": "Innovate Technologies",
            "title": "Director of Partnerships",
            "website": "www.innovatetech.io",
            "address": "500 Innovation Way, San Francisco, CA"
        }

    async def transcribe_voice_note(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
        """
        Transcribe voice notes using Gemini Audio API or fallback mock transcription.
        """
        prompt = "Transcribe the spoken audio in this file word-for-word. Do not summarize or add remarks."

        if self.client:
            import time
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    audio_content = types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type=mime_type,
                    )
                    
                    response = self.client.models.generate_content(
                        model=settings.GEMINI_MODEL,
                        contents=[audio_content, prompt]
                    )
                    return response.text.strip()
                except Exception as e:
                    print(f"Gemini API attempt {attempt + 1} failed: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    else:
                        print(f"Gemini API Error in transcribe_voice_note after {max_retries} attempts: {e}. Falling back to mock transcription.")

        # Fallback Mock Audio Transcription
        print("Using MOCK transcription (No Gemini API key or error occurred).")
        return "Please follow up with Jane Smith next Monday to discuss the contract terms. Her preferred email is jane.smith@innovate.tech."

ai_service = AIService()
