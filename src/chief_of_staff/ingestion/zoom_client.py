"""Zoom API client — OAuth authentication and core API operations.

Supports Zoom Server-to-Server OAuth (for automated access without user login)
as well as standard OAuth 2.0 for user-level access.

Server-to-Server is recommended for the Chief of Staff since it runs autonomously.
Set up at: https://marketplace.zoom.us/ > Develop > Build App > Server-to-Server OAuth
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from chief_of_staff.config import settings

logger = logging.getLogger(__name__)

ZOOM_OAUTH_URL = "https://zoom.us/oauth/token"
ZOOM_API_BASE = "https://api.zoom.us/v2"

# Cached token
_access_token: str | None = None
_token_expires_at: float = 0


async def get_access_token() -> str:
    """Get a valid Zoom access token, refreshing if expired.

    Uses Server-to-Server OAuth (client_credentials grant).
    """
    global _access_token, _token_expires_at

    if _access_token and time.time() < _token_expires_at - 60:
        return _access_token

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            ZOOM_OAUTH_URL,
            params={"grant_type": "account_credentials", "account_id": settings.zoom_account_id},
            auth=(settings.zoom_client_id, settings.zoom_client_secret),
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

    _access_token = data["access_token"]
    _token_expires_at = time.time() + data.get("expires_in", 3600)
    logger.info("Zoom access token refreshed")
    return _access_token


async def zoom_api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make an authenticated GET request to the Zoom API."""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{ZOOM_API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def zoom_api_post(path: str, json_body: dict[str, Any] | None = None) -> dict[str, Any]:
    """Make an authenticated POST request to the Zoom API."""
    token = await get_access_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{ZOOM_API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            json=json_body or {},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()


async def list_users() -> list[dict[str, Any]]:
    """List all users on the Zoom account."""
    data = await zoom_api_get("/users", params={"page_size": 100})
    return data.get("users", [])


async def list_meetings(user_id: str = "me", meeting_type: str = "scheduled") -> list[dict[str, Any]]:
    """List meetings for a user.

    Args:
        user_id: Zoom user ID or email, or 'me' for the authenticated user.
        meeting_type: 'scheduled', 'live', 'upcoming', 'previous_meetings'.
    """
    data = await zoom_api_get(
        f"/users/{user_id}/meetings",
        params={"type": meeting_type, "page_size": 50},
    )
    return data.get("meetings", [])


async def get_meeting(meeting_id: int | str) -> dict[str, Any]:
    """Get details of a specific meeting."""
    return await zoom_api_get(f"/meetings/{meeting_id}")


async def list_recordings(
    user_id: str = "me",
    from_date: str | None = None,
    to_date: str | None = None,
) -> list[dict[str, Any]]:
    """List cloud recordings for a user.

    Args:
        user_id: Zoom user ID or email.
        from_date: Start date (YYYY-MM-DD). Defaults to 30 days ago.
        to_date: End date (YYYY-MM-DD). Defaults to today.
    """
    from datetime import datetime, timedelta

    if not from_date:
        from_date = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not to_date:
        to_date = datetime.utcnow().strftime("%Y-%m-%d")

    data = await zoom_api_get(
        f"/users/{user_id}/recordings",
        params={"from": from_date, "to": to_date, "page_size": 50},
    )
    return data.get("meetings", [])


async def get_recording_transcript(download_url: str) -> str:
    """Download a recording transcript (VTT format) from Zoom.

    The download URL comes from the recording files list and requires
    an access token for authentication.
    """
    token = await get_access_token()
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(
            download_url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.text
