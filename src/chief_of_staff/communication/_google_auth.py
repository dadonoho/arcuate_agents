"""Google API authentication helper — shared across Gmail and Google Docs connectors."""

from __future__ import annotations

import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from chief_of_staff.config import settings

# Scopes needed for Gmail read/send and Google Docs/Drive read
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

_credentials: Credentials | None = None


def get_credentials() -> Credentials:
    """Get valid Google OAuth2 credentials, refreshing or running OAuth flow as needed."""
    global _credentials

    if _credentials and _credentials.valid:
        return _credentials

    token_path = Path(settings.google_token_path)
    creds_path = Path(settings.google_credentials_path)

    if token_path.exists():
        _credentials = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if _credentials and _credentials.expired and _credentials.refresh_token:
        _credentials.refresh(Request())
    elif not _credentials or not _credentials.valid:
        if not creds_path.exists():
            raise FileNotFoundError(
                f"Google credentials file not found at {creds_path}. "
                "Download it from Google Cloud Console > APIs & Services > Credentials."
            )
        flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
        _credentials = flow.run_local_server(port=0)

    # Save token for next run
    if _credentials:
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
