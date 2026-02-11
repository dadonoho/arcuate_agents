# Arcuate Chief of Staff — Setup Guide

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url> && cd arcuate_agents
pip install -e ".[dev]"
```

### 2. Configure credentials

Copy `.env.example` to `.env` and fill in your keys (already done if you used the setup script).

### 3. Google OAuth Setup

The Chief of Staff needs access to Gmail (read + send) and Google Docs/Drive (read).

**a) Get OAuth credentials:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing)
3. Enable APIs: Gmail API, Google Docs API, Google Drive API
4. Go to APIs & Services > Credentials
5. Create OAuth 2.0 Client ID (type: **Desktop Application**)
6. Download the JSON file
7. Save it as `credentials.json` in the project root

**b) Run the OAuth flow:**
```bash
python scripts/setup_google_auth.py
```
This opens a browser window. Sign in with the email account that will be the Chief of Staff's inbox (e.g., the one that receives forwarded emails from all founders).

**c) Set up email forwarding:**
Each founder should set up auto-forwarding in their Gmail:
- Settings > Forwarding > Add forwarding address > `<chief-email>`

### 4. Validate credentials

```bash
python scripts/validate_credentials.py
```

This checks all API keys, phone numbers, and Google auth. Fix any failures before proceeding.

### 5. Zoom Setup

The Chief of Staff auto-ingests Zoom meeting transcripts. Two options:

**Option A: Zoom Cloud Recordings (recommended to start)**

Pull transcripts from Zoom's built-in cloud recording feature.

1. Go to [marketplace.zoom.us](https://marketplace.zoom.us/) > Develop > Build App
2. Choose **Server-to-Server OAuth**
3. Add scopes: `recording:read:admin`, `user:read:admin`, `meeting:read:admin`
4. Copy Account ID, Client ID, Client Secret into `.env`
5. Enable cloud recording in Zoom Settings > Recording > Cloud recording
6. Enable "Audio transcript" under cloud recording settings

**Option B: Recall.ai Meeting Bot (auto-joins any meeting)**

A bot that joins meetings automatically, records, and transcribes.

1. Sign up at [recall.ai](https://www.recall.ai/)
2. Get your API key from the Recall dashboard
3. Set `RECALL_API_KEY` in `.env`
4. Set `WEBHOOK_BASE_URL` to your public server URL

The bot can join Zoom, Google Meet, and Microsoft Teams.

**Zoom Webhooks (real-time ingestion)**

For automatic ingestion when recordings complete:

1. In your Zoom app on marketplace.zoom.us, go to Feature > Event Subscriptions
2. Add subscription with endpoint: `https://your-server.com/webhooks/zoom`
3. Subscribe to: `meeting.started`, `meeting.ended`, `recording.completed`, `recording.transcript_completed`
4. Copy the Secret Token and set `ZOOM_WEBHOOK_SECRET` in `.env`

### 6. Initial data ingestion

Backfill historical data:
```bash
# Everything
python scripts/ingest_initial.py

# Or one at a time
python scripts/ingest_initial.py --emails-only
python scripts/ingest_initial.py --docs-only
python scripts/ingest_initial.py --transcripts-only
python scripts/ingest_initial.py --zoom-only --zoom-days-back 90
```

### 7. Run the server

```bash
uvicorn chief_of_staff.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Configure Twilio SMS webhook

In the Twilio Console:
1. Go to Phone Numbers > Manage > Active Numbers
2. Click your number
3. Under "Messaging", set the webhook URL:
   - **When a message comes in:** `https://your-server.com/webhooks/twilio/sms` (POST)
   - For local dev, use [ngrok](https://ngrok.com/): `ngrok http 8000`

### 9. Test it

Text your Twilio number from your phone! The Chief of Staff should respond.

You can also test via the API:
```bash
# Ask a question
curl -X POST "http://localhost:8000/api/ask?query=What+do+you+know+about+our+clients"

# Ingest Zoom recordings from the last 30 days
curl -X POST "http://localhost:8000/api/ingest/zoom?days_back=30"

# Send a meeting bot to join a Zoom call
curl -X POST "http://localhost:8000/api/meetings/send-bot?meeting_url=https://zoom.us/j/123456&meeting_title=Team+Standup"

# List active meeting bots
curl "http://localhost:8000/api/meetings/bots"
```

## Twilio Phone Numbers

Run the validation script to see available numbers on your account.
Set `TWILIO_PHONE_NUMBER` in `.env` to one of them (E.164 format: `+1XXXXXXXXXX`).

If you need a new number dedicated to the Chief of Staff, buy one in the Twilio Console.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design.
