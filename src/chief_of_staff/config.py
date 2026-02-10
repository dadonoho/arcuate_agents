"""Configuration and settings for the Chief of Staff agent."""

from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-20250929"

    # Twilio
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_phone_number: str = ""

    # ElevenLabs
    elevenlabs_api_key: str = ""

    # Google
    google_credentials_path: str = "./credentials.json"
    google_token_path: str = "./token.json"

    # Agent config
    chief_email: str = ""
    founder_phone_numbers: list[str] = []

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Knowledge store
    chroma_persist_dir: str = "./chroma_data"
    sqlite_db_path: str = "./chief_of_staff.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
