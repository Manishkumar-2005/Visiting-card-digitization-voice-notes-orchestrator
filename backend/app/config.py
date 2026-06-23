import os
import json
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

class Settings(BaseSettings):
    # App Config
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    PORT: int = Field(default=8000, env="PORT")
    
    # AI Config
    GEMINI_API_KEY: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    GEMINI_MODEL: str = Field(default="gemini-3.5-flash", env="GEMINI_MODEL")
    
    # DB Config
    MONGODB_URI: Optional[str] = Field(default=None, env="MONGODB_URI")
    DB_NAME: str = Field(default="visiting_cards", env="DB_NAME")
    
    # Google Sheets Config
    GOOGLE_CREDENTIALS_JSON: Optional[str] = Field(default=None, env="GOOGLE_CREDENTIALS_JSON")
    GOOGLE_SHEET_NAME: str = Field(default="Visiting Cards Orchestrator", env="GOOGLE_SHEET_NAME")
    
    # WhatsApp Config
    WHATSAPP_TOKEN: Optional[str] = Field(default=None, env="WHATSAPP_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = Field(default=None, env="WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_RECIPIENT_PHONE: Optional[str] = Field(default=None, env="WHATSAPP_RECIPIENT_PHONE")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    @property
    def is_sheets_configured(self) -> bool:
        return self.GOOGLE_CREDENTIALS_JSON is not None and len(self.GOOGLE_CREDENTIALS_JSON.strip()) > 0

    @property
    def is_whatsapp_configured(self) -> bool:
        return (
            self.WHATSAPP_TOKEN is not None
            and self.WHATSAPP_PHONE_NUMBER_ID is not None
            and self.WHATSAPP_RECIPIENT_PHONE is not None
        )

    @property
    def is_mongodb_configured(self) -> bool:
        return self.MONGODB_URI is not None and len(self.MONGODB_URI.strip()) > 0

    @property
    def get_google_credentials_dict(self) -> Optional[dict]:
        if not self.is_sheets_configured:
            return None
        try:
            return json.loads(self.GOOGLE_CREDENTIALS_JSON)
        except Exception as e:
            print(f"Error parsing GOOGLE_CREDENTIALS_JSON: {e}")
            return None

settings = Settings()
