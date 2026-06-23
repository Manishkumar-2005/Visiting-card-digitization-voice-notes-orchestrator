import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from app.config import settings

# Try to import Google Sheets dependencies
try:
    import gspread
    from google.oauth2.service_account import Credentials
    HAS_GSPREAD = True
except ImportError:
    HAS_GSPREAD = False

logger = logging.getLogger(__name__)

class SheetsService:
    def __init__(self):
        self.client = None
        self.sheet = None
        self.mock_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data",
            "mock_google_sheets.json"
        )
        # Ensure data directory exists for mock files
        os.makedirs(os.path.dirname(self.mock_file_path), exist_ok=True)
        
        # Initialize Mock DB if file doesn't exist
        if not os.path.exists(self.mock_file_path):
            self._save_mock_data([])

        if HAS_GSPREAD and settings.is_sheets_configured:
            try:
                creds_dict = settings.get_google_credentials_dict
                if creds_dict:
                    scopes = [
                        'https://www.googleapis.com/auth/spreadsheets',
                        'https://www.googleapis.com/auth/drive'
                    ]
                    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
                    self.client = gspread.authorize(creds)
                    # Try to open the sheet, otherwise create it or log error
                    try:
                        self.sheet = self.client.open(settings.GOOGLE_SHEET_NAME).sheet1
                        logger.info(f"Connected to Google Sheet: {settings.GOOGLE_SHEET_NAME}")
                        # If the sheet is empty (no headers), add headers to establish table columns
                        try:
                            first_row = self.sheet.row_values(1)
                            first_row_clean = [v for v in first_row if str(v).strip()]
                            if not first_row_clean:
                                headers = [
                                    "Name", "Phone", "Email", "Company", "Title", 
                                    "Website", "Address", "Voice Notes", "Audio URL", "Created At"
                                ]
                                self.sheet.update(values=[headers], range_name="A1:J1")
                                logger.info("Added headers to pre-existing Google Sheet in Row 1.")
                        except Exception as eh:
                            logger.error(f"Error checking/adding headers: {eh}")
                    except gspread.exceptions.SpreadsheetNotFound:
                        # Create sheet if not found
                        logger.warning(f"Google Sheet '{settings.GOOGLE_SHEET_NAME}' not found. Attempting to create it...")
                        sh = self.client.create(settings.GOOGLE_SHEET_NAME)
                        # Note: User must share this spreadsheet or use service account email to see it.
                        self.sheet = sh.sheet1
                        headers = [
                            "Name", "Phone", "Email", "Company", "Title", 
                            "Website", "Address", "Voice Notes", "Audio URL", "Created At"
                        ]
                        self.sheet.update(values=[headers], range_name="A1:J1")
                        logger.info(f"Created new Google Sheet: {settings.GOOGLE_SHEET_NAME}")
            except Exception as e:
                logger.error(f"Failed to initialize Google Sheets connection: {e}. Falling back to Mock Sheets.")

    def _get_mock_data(self) -> List[Dict[str, Any]]:
        try:
            with open(self.mock_file_path, "r") as f:
                return json.load(f)
        except Exception:
            return []

    def _save_mock_data(self, data: List[Dict[str, Any]]):
        try:
            with open(self.mock_file_path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"Failed to write to mock sheets file: {e}")

    async def find_contact_by_email_or_phone(self, email: str, phone: str) -> Optional[Dict[str, Any]]:
        """
        Check if contact already exists by email or phone.
        """
        email = (email or "").strip().lower()
        phone = (phone or "").strip()

        # Try Google Sheets
        if self.sheet:
            try:
                records = self.sheet.get_all_records()
                for row in records:
                    row_email = str(row.get("Email", "")).strip().lower()
                    row_phone = str(row.get("Phone", "")).strip()
                    if (email and row_email == email) or (phone and row_phone == phone):
                        return {
                            "name": row.get("Name", ""),
                            "phone": row.get("Phone", ""),
                            "email": row.get("Email", ""),
                            "company": row.get("Company", ""),
                            "title": row.get("Title", ""),
                            "website": row.get("Website", ""),
                            "address": row.get("Address", ""),
                            "notes": row.get("Voice Notes", ""),
                            "audio_url": row.get("Audio URL", ""),
                            "created_at": row.get("Created At", "")
                        }
                return None  # Connection was active, so treat Sheets as single source of truth
            except Exception as e:
                logger.error(f"Google Sheets error in find_contact_by_email_or_phone: {e}")
        
        # Mock Sheets Fallback
        mock_data = self._get_mock_data()
        for contact in mock_data:
            c_email = str(contact.get("email", "")).strip().lower()
            c_phone = str(contact.get("phone", "")).strip()
            if (email and c_email == email) or (phone and c_phone == phone):
                return contact
                
        return None

    async def add_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add a new contact to Google Sheets and SQLite mock DB.
        """
        now_str = datetime.now().isoformat()
        
        row_data = {
            "name": contact.get("name", ""),
            "phone": contact.get("phone", ""),
            "email": contact.get("email", ""),
            "company": contact.get("company", ""),
            "title": contact.get("title", ""),
            "website": contact.get("website", ""),
            "address": contact.get("address", ""),
            "notes": contact.get("notes", ""),
            "audio_url": contact.get("audio_url", ""),
            "created_at": now_str
        }

        # Save to Google Sheet
        if self.sheet:
            try:
                row_list = [
                    row_data["name"],
                    row_data["phone"],
                    row_data["email"],
                    row_data["company"],
                    row_data["title"],
                    row_data["website"],
                    row_data["address"],
                    row_data["notes"],
                    row_data["audio_url"],
                    row_data["created_at"]
                ]
                self.sheet.append_row(row_list)
                logger.info(f"Logged to Google Sheet: {row_data['email']}")
            except Exception as e:
                logger.error(f"Google Sheets error in add_contact: {e}")

        # Always save to mock sheets file as local mirror and fallback
        mock_data = self._get_mock_data()
        mock_data.append(row_data)
        self._save_mock_data(mock_data)
        return row_data

    async def update_contact_notes_and_audio(self, email: str, notes: str, audio_url: str = "") -> bool:
        """
        Update the notes and audio URL for a contact identified by email.
        """
        email = (email or "").strip().lower()
        updated = False

        # Update Google Sheets
        if self.sheet:
            try:
                records = self.sheet.get_all_records()
                for idx, row in enumerate(records):
                    row_email = str(row.get("Email", "")).strip().lower()
                    if row_email == email:
                        # gspread rows are 1-indexed, and header is row 1
                        sheet_row_num = idx + 2
                        
                        # Fetch existing notes if any, and append the new notes
                        existing_notes = str(row.get("Voice Notes", "")).strip()
                        combined_notes = f"{existing_notes} | {notes}" if existing_notes else notes
                        
                        # Column positions: Voice Notes is col 8, Audio URL is col 9
                        self.sheet.update_cell(sheet_row_num, 8, combined_notes)
                        if audio_url:
                            self.sheet.update_cell(sheet_row_num, 9, audio_url)
                        updated = True
                        logger.info(f"Updated Google Sheets entry for {email}")
                        break
            except Exception as e:
                logger.error(f"Google Sheets error in update_contact_notes_and_audio: {e}")

        # Update Mock Sheets file
        mock_data = self._get_mock_data()
        for contact in mock_data:
            c_email = str(contact.get("email", "")).strip().lower()
            if c_email == email:
                existing_notes = str(contact.get("notes", "")).strip()
                contact["notes"] = f"{existing_notes} | {notes}" if existing_notes else notes
                if audio_url:
                    contact["audio_url"] = audio_url
                contact["updated_at"] = datetime.now().isoformat()
                updated = True
                break
        
        if updated:
            self._save_mock_data(mock_data)
        
        return updated

    async def get_all_contacts(self) -> List[Dict[str, Any]]:
        if self.sheet:
            try:
                records = self.sheet.get_all_records()
                formatted_records = []
                for row in records:
                    formatted_records.append({
                        "name": row.get("Name", ""),
                        "phone": row.get("Phone", ""),
                        "email": row.get("Email", ""),
                        "company": row.get("Company", ""),
                        "title": row.get("Title", ""),
                        "website": row.get("Website", ""),
                        "address": row.get("Address", ""),
                        "notes": row.get("Voice Notes", ""),
                        "audio_url": row.get("Audio URL", ""),
                        "created_at": row.get("Created At", "")
                    })
                return formatted_records
            except Exception as e:
                logger.error(f"Google Sheets error in get_all_contacts: {e}")
        
        return self._get_mock_data()

sheets_service = SheetsService()
