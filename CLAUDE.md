# Arcuate Chief of Staff Agent

## What This Is
AI Chief of Staff for Arcuate Health — a healthcare startup doing agentic outreach for aesthetic practices.
The agent ingests all company knowledge (emails, docs, call transcripts) and lets founders interact via WhatsApp/SMS.

## Founders
- Dhiraj Pangal: +19256993247
- 4 part-time founders total

## Data Sources
- **Gmail** — chief@arcuate.health inbox (Google OAuth)
- **Google Docs** — shared drive documents (Google OAuth)
- **ElevenLabs** — AI call transcripts with leads/clients
- (Zoom — not configured yet, credentials blank)

## Credentials (in .env, gitignored)
- Anthropic API key: configured
- Twilio: configured (SID, token, phone +18888854780)
- ElevenLabs: configured
- Google OAuth: credentials.json present, need to run OAuth flow for token.json
- Zoom: NOT configured (blank in .env)
- Recall.ai: NOT configured

## Architecture
FastAPI server → Twilio webhook receives SMS/WhatsApp → Claude agent reasons with tool use → searches knowledge base (ChromaDB + SQLite) → responds via Twilio

## Communication Channel
WhatsApp via Twilio (default). Can switch to SMS by setting MESSAGING_CHANNEL=sms in .env.

## Deployment
Target: GCP Compute Engine VM (project: agents-arcuate)
- Static IP with HTTP webhook for Twilio
- systemd service for the FastAPI app
- Periodic ingestion via background scheduler

## Key Commands
- Run server: `cd /Users/dhirajpangal/Desktop/arcuate_agents && source venv/bin/activate && python -m uvicorn chief_of_staff.main:app --host 0.0.0.0 --port 8000`
- Run OAuth: `python scripts/setup_google_auth.py`
- Initial ingestion: `python scripts/ingest_initial.py`
- Validate creds: `python scripts/validate_credentials.py`
