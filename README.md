# Arcuate Chief of Staff Agent

AI Chief of Staff for Arcuate Health — a unified knowledge + communication agent that serves as the central nervous system for the company.

## What It Does

The Chief of Staff ingests **all company information** (emails, Google Docs, call transcripts, Zoom meetings) into a searchable knowledge base and lets founders interact with it via **SMS text messages**. It can answer questions, draft documents, send communications, and dispatch meeting bots — all with full company context.

**Example:** Text "Create an onboarding packet for Dr. Smith" and the agent pulls the old onboarding template from Google Docs, email chains with Dr. Smith, ElevenLabs call transcripts, and synthesizes a new packet.

## Current Status

### Built (this session)

- **Agent Core** — Claude-powered reasoning loop with tool use (`src/chief_of_staff/agent/`)
- **Knowledge Store** — ChromaDB vector search + SQLite metadata (`src/chief_of_staff/knowledge/`)
- **Ingestion Layer**
  - Gmail connector (fetch + ingest emails)
  - Google Docs/Drive connector
  - ElevenLabs transcript puller
  - Zoom cloud recording ingestion (VTT transcript parser)
  - Recall.ai meeting bot (auto-join, record, transcribe)
  - Manual meeting transcript upload
- **Communication Layer**
  - Twilio SMS (send/receive — primary founder interface)
  - Gmail send (via Google API)
  - Voice placeholder (Twilio + ElevenLabs)
- **FastAPI Server** with webhooks for:
  - Twilio SMS (incoming texts from founders)
  - Gmail push notifications (new emails)
  - Zoom events (meeting started/ended, recording completed)
  - Recall.ai events (bot status, transcript delivery)
- **Setup tooling** — credential validation script, Google OAuth helper, initial ingestion script

### Not Yet Done

- [ ] **Deploy and test end-to-end** — run locally with real credentials, test SMS flow
- [ ] **Twilio phone number** — need to set `TWILIO_PHONE_NUMBER` in `.env` (run `validate_credentials.py` to find available numbers)
- [ ] **Google OAuth flow** — need to copy `credentials.json` and run `setup_google_auth.py`
- [ ] **Zoom credentials** — need Server-to-Server OAuth app from marketplace.zoom.us
- [ ] **Recall.ai account** — sign up and get API key (optional, for meeting bot)
- [ ] **Voice interface** — implement Twilio Voice + ElevenLabs TTS for phone calls with the agent
- [ ] **Scheduled ingestion** — cron/background task to periodically sync emails, docs, transcripts
- [ ] **Conversation memory** — persistent multi-turn conversation context per founder (beyond recent SMS history)
- [ ] **Google Calendar integration** — auto-detect upcoming meetings and dispatch bots
- [ ] **Slack integration** — another founder interface beyond SMS
- [ ] **Web dashboard** — view knowledge base, task history, agent activity
- [ ] **Document output** — create Google Docs directly (not just draft in chat)
- [ ] **The other 13 agents** — build out the full 14-agent orchestration system
- [ ] **Inter-agent communication** — protocol for agents to delegate tasks to each other
- [ ] **Production deployment** — Docker, cloud hosting, HTTPS, monitoring

## Quick Start

See [SETUP.md](SETUP.md) for full instructions.

```bash
git clone https://github.com/pangal-nsgy/arcuate_agents.git
cd arcuate_agents
git checkout claude/mcp-chrome-extension-BW3zj
pip install -e ".[dev]"
cp .env.example .env   # Fill in your API keys
python scripts/validate_credentials.py
python scripts/ingest_initial.py
uvicorn chief_of_staff.main:app --reload
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the full system design diagram.

## Project Structure

```
src/chief_of_staff/
├── main.py                    # FastAPI server entry point
├── config.py                  # Settings from .env
├── agent/
│   ├── core.py                # Claude reasoning loop with tool use
│   ├── planner.py             # Multi-step task decomposition
│   └── tools.py               # Agent tools (search, SMS, email, meetings)
├── ingestion/
│   ├── gmail.py               # Gmail API email ingestion
│   ├── gdocs.py               # Google Docs/Drive ingestion
│   ├── elevenlabs.py          # ElevenLabs transcript ingestion
│   ├── zoom.py                # Zoom cloud recording ingestion
│   ├── zoom_client.py         # Zoom API client (OAuth, recordings)
│   ├── recall_bot.py          # Recall.ai meeting bot
│   └── meetings.py            # Manual meeting transcript ingestion
├── knowledge/
│   ├── store.py               # Unified knowledge interface
│   ├── vectordb.py            # ChromaDB semantic search
│   ├── database.py            # SQLite structured metadata
│   └── embeddings.py          # Text chunking utilities
├── communication/
│   ├── sms.py                 # Twilio SMS
│   ├── email.py               # Gmail send
│   ├── voice.py               # Voice (placeholder)
│   └── _google_auth.py        # Google OAuth helper
└── webhooks/
    ├── twilio.py              # SMS webhook
    ├── gmail.py               # Email push notifications
    ├── zoom.py                # Zoom meeting events
    └── recall.py              # Recall.ai bot events
```
