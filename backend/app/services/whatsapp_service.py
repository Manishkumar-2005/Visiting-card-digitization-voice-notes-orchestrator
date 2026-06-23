import os
import logging
import httpx
from typing import Dict, Any, Optional
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    def __init__(self):
        self.token = settings.WHATSAPP_TOKEN
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.recipient_phone = settings.WHATSAPP_RECIPIENT_PHONE
        
        self.mock_log_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data",
            "mock_whatsapp_notifications.log"
        )
        os.makedirs(os.path.dirname(self.mock_log_path), exist_ok=True)

    async def send_card_logged_notification(self, name: str, company: str, email: str, phone: str) -> Dict[str, Any]:
        """
        Send a notification to the manager alerting them that a new contact has been logged.
        """
        message_body = (
            f"🔔 *New Visiting Card Logged!*\n\n"
            f"👤 *Name:* {name}\n"
            f"🏢 *Company:* {company}\n"
            f"📧 *Email:* {email}\n"
            f"📞 *Phone:* {phone}\n\n"
            f"Logged at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        if settings.is_whatsapp_configured:
            url = f"https://graph.facebook.com/v18.0/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }
            
            # Note: For Sandbox / Test accounts, WhatsApp requires template messages or 
            # text messages if a session is already active. We send a standard text message.
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": self.recipient_phone,
                "type": "text",
                "text": {
                    "body": message_body
                }
            }

            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers, json=payload, timeout=10.0)
                    response_data = response.json()
                    
                    if response.status_code == 200:
                        logger.info(f"WhatsApp notification sent successfully: {response_data}")
                        return {
                            "status": "success",
                            "method": "live_whatsapp",
                            "response": response_data
                        }
                    else:
                        logger.error(f"WhatsApp API returned error {response.status_code}: {response_data}")
                        # Fallback to mock log on failure
            except Exception as e:
                logger.error(f"Exception while sending WhatsApp notification: {e}")
                # Fallback to mock log on failure

        # Mock Notification Logging
        log_entry = (
            f"--------------------------------------------------\n"
            f"TIMESTAMP: {datetime.now().isoformat()}\n"
            f"RECIPIENT: {self.recipient_phone or 'MOCK_MANAGER'}\n"
            f"MESSAGE:\n{message_body}\n"
            f"--------------------------------------------------\n"
        )
        
        try:
            with open(self.mock_log_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to write to mock WhatsApp log: {e}")

        logger.info("WhatsApp notification sent via MOCK channel.")
        return {
            "status": "success",
            "method": "mock_whatsapp_log",
            "message": "Logged notification to local file because WhatsApp API is not configured or failed.",
            "body": message_body
        }

whatsapp_service = WhatsAppService()
