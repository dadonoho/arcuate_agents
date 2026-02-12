"""Google API authentication helper — shared across Gmail and Google Docs connectors."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from chief_of_staff.config import settings

logger = logging.getLogger(__name__)

# Scopes needed for Gmail read/send and Google Docs/Drive read
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

_credentials: Credentials | None = None


def get_credentials() -> Credentials:
    """Get valid Google OAuth2 credentials, refreshing or running OAuth flow as needed.

    Supports two modes:
    - File-based: reads credentials.json and token.json from disk (local dev)
    - Env-based: reads GOOGLE_TOKEN_JSON env var (Railway/Docker deployment)
    """
    global _credentials

    if _credentials and _credentials.valid:
        return _credentials

    token_path = Path(settings.google_token_path)

    # Try loading token from env var first (Railway/Docker), then file
    if settings.google_token_json:
        token_data = json.loads(settings.google_token_json)
        _credentials = Credentials.from_authorized_user_info(token_data, SCOPES)
    elif token_path.exists():
        _credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if _credentials and _credentials.expired and _credentials.refresh_token:
        _credentials.refresh(Request())
        # Persist refreshed token back to env-compatible format
        if settings.google_token_json:
            logger.info("Token refreshed (running from env var — token auto-refreshes in memory)")
        else:
            token_path.write_text(_credentials.to_json())
    elif not _credentials or not _credentials.valid:
        # Need to run interactive OAuth flow (only works locally)
        creds_path = Path(settings.google_credentials_path)
        if settings.google_credentials_json:
            # Write temp file for InstalledAppFlow
            creds_path = Path("/tmp/google_credentials.json")
            creds_path.write_text(settings.google_credentials_json)
        if not creds_path.exists():
            raise FileNotFoundError(
                f"Google credentials file not found at {creds_path}. "
                "Download it from Google Cloud Console > APIs & Services > Credentials."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
        _credentials = flow.run_local_server(port=0)

    # Save token for next run (file mode only)
    if _credentials and not settings.google_token_json:
        token_path.write_text(_credentials.to_json())

    return _credentials


def get_gmail_service():
    """Get an authenticated Gmail API service instance."""
    creds = get_credentials()
    return build("gmail", "v1", credentials=creds)


def get_docs_service():
    """Get an authenticated Google Docs API service instance."""
    creds = get_credentials()
    return build("docs", "v1", credentials=creds)


def get_drive_service():
    """Get an authenticated Google Drive API service instance."""
    creds = get_credentials()
    return build("drive", "v3", credentials=creds)
