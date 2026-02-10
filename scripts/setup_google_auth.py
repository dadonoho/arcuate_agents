#!/usr/bin/env python3
"""Google OAuth setup helper.

Run this interactively to complete the OAuth flow and generate token.json.

Prerequisites:
1. Go to Google Cloud Console > APIs & Services > Credentials
2. Create an OAuth 2.0 Client ID (Desktop application)
3. Download the JSON and save as credentials.json in the project root

Usage:
    python scripts/setup_google_auth.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from chief_of_staff.communication._google_auth import get_credentials


def main():
    print("Google OAuth Setup")
    print("=" * 40)
    print()
    print("This will open a browser window for you to authorize access to:")
    print("  - Gmail (read + send)")
    print("  - Google Docs (read)")
    print("  - Google Drive (read)")
    print()
    print("Make sure credentials.json is in the project root.")
    print()

    try:
        creds = get_credentials()
        print()
        print("Authentication successful!")
        print(f"Token saved. Valid: {creds.valid}")
        print("You can now run the agent.")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Download your OAuth credentials from:")
        print("  Google Cloud Console > APIs & Services > Credentials")
        sys.exit(1)
    except Exception as e:
        print(f"Error during authentication: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
