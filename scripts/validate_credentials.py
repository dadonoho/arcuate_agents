#!/usr/bin/env python3
"""Validate all credentials before running the agent.

Run this locally to check that all API keys and credentials are working.

Usage:
    python scripts/validate_credentials.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def check(name: str, ok: bool, detail: str = ""):
    status = "OK" if ok else "FAIL"
    icon = "+" if ok else "!"
    msg = f"  [{icon}] {name}: {status}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    return ok


async def main():
    print("=" * 50)
    print("Arcuate Chief of Staff — Credential Validation")
    print("=" * 50)
    print()

    from chief_of_staff.config import settings

    all_ok = True

    # 1. Anthropic
    print("[Anthropic]")
    if settings.anthropic_api_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
            msg = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Say ok"}],
            )
            all_ok &= check("API Key", True, f"Model: {settings.anthropic_model}")
        except Exception as e:
            all_ok &= check("API Key", False, str(e))
    else:
        all_ok &= check("API Key", False, "Not set")
    print()

    # 2. Twilio
    print("[Twilio]")
    if settings.twilio_account_sid and settings.twilio_auth_token:
        try:
            from twilio.rest import Client
            client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
            account = client.api.accounts(settings.twilio_account_sid).fetch()
            all_ok &= check("Account", True, f"Status: {account.status}")

            numbers = client.incoming_phone_numbers.list(limit=10)
            if numbers:
                for n in numbers:
                    print(f"      Phone: {n.phone_number} ({n.friendly_name})")
                if not settings.twilio_phone_number:
                    print(f"      SUGGESTION: Set TWILIO_PHONE_NUMBER={numbers[0].phone_number}")
                all_ok &= check("Phone Numbers", True, f"{len(numbers)} found")
            else:
                all_ok &= check("Phone Numbers", False, "No numbers on account")
        except Exception as e:
            all_ok &= check("Account", False, str(e))
    else:
        all_ok &= check("Credentials", False, "SID or Auth Token not set")

    if settings.twilio_phone_number:
        all_ok &= check("Phone Number", True, settings.twilio_phone_number)
    else:
        all_ok &= check("Phone Number", False, "TWILIO_PHONE_NUMBER not set — run this script locally to see available numbers")
    print()

    # 3. ElevenLabs
    print("[ElevenLabs]")
    if settings.elevenlabs_api_key:
        try:
            import httpx
            r = httpx.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": settings.elevenlabs_api_key},
                timeout=10,
            )
            if r.status_code == 200:
                user = r.json()
                all_ok &= check("API Key", True, f"User: {user.get('first_name', 'unknown')}")
            else:
                all_ok &= check("API Key", False, f"HTTP {r.status_code}")
        except Exception as e:
            all_ok &= check("API Key", False, str(e))
    else:
        all_ok &= check("API Key", False, "Not set")
    print()

    # 4. Google
    print("[Google OAuth]")
    creds_path = Path(settings.google_credentials_path)
    if creds_path.exists():
        all_ok &= check("Credentials File", True, str(creds_path))
        token_path = Path(settings.google_token_path)
        if token_path.exists():
            all_ok &= check("Token File", True, "Found — trying to use it")
            try:
                from chief_of_staff.communication._google_auth import get_gmail_service
                service = get_gmail_service()
                profile = service.users().getProfile(userId="me").execute()
                all_ok &= check("Gmail Access", True, f"Email: {profile.get('emailAddress')}")
            except Exception as e:
                all_ok &= check("Gmail Access", False, f"Run: python scripts/setup_google_auth.py — {e}")
        else:
            all_ok &= check("Token File", False, "Run: python scripts/setup_google_auth.py")
    else:
        all_ok &= check("Credentials File", False, f"Not found at {creds_path}. Download from Google Cloud Console.")
    print()

    # 5. Founder config
    print("[Agent Config]")
    if settings.founder_phone_numbers:
        all_ok &= check("Founder Phones", True, f"{len(settings.founder_phone_numbers)} configured")
    else:
        all_ok &= check("Founder Phones", False, "FOUNDER_PHONE_NUMBERS not set")
    print()

    # Summary
    print("=" * 50)
    if all_ok:
        print("All checks passed! Ready to run:")
        print("  uvicorn chief_of_staff.main:app --reload")
    else:
        print("Some checks failed. Fix the issues above, then re-run.")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
