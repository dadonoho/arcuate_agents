# Arcuate Chief of Staff Agent

## What This Is
AI Chief of Staff for Arcuate Health — a healthcare startup doing agentic outreach for aesthetic practices (ElevenLabs + Twilio voice calls to practices).
The agent ingests all company knowledge and lets founders interact via Discord.

## Founders
- Dhiraj Pangal: +19256993247 (Discord: dhirajarcuate)
- 4 part-time founders total

## Current Status (as of 2026-02-12)
- **Discord bot is WORKING** — "Arcuate Chief of Staff#7949" (bot ID: 1471658651491106847)
- **Knowledge base loaded**: 501 emails, 27 Google Docs, 35 ElevenLabs transcripts
- **Railway deployment**: build failed — needs debugging (Dockerfile issue likely)
- **Local server**: works perfectly on localhost:8000
- **SMS via Twilio**: sends from API but Dhiraj says he doesn't receive texts — skip SMS, use Discord
- **Background scheduler**: syncs all sources hourly (non-blocking, uses thread pool)

## Communication Channel
**Discord** (primary). Bot responds to:
- DMs to the bot
- @mentions in any channel
- Messages in channels listed in DISCORD_CHANNELS config (default: chief-of-staff, arcuatechat)

SMS/WhatsApp via Twilio is built but not working for delivery. Discord is the active interface.

## Data Sources
- **Gmail** — authenticated via OAuth (token.json present locally)
- **Google Docs** — same OAuth token, reads all docs in the account
- **ElevenLabs** — AI call transcripts (Conversational AI API)
- Zoom/Recall.ai — code built but credentials not configured

## Credentials & Local Files (all in repo root, all gitignored)
- `.env` — all API keys and config
- `credentials.json` — Google OAuth client (Desktop app type, project: agents-arcuate)
- `token.json` — Google OAuth refresh token (auto-refreshes)
- `chief_of_staff.db` — SQLite with document metadata + conversation history
- `chroma_data/` — ChromaDB vector embeddings (~33MB)

## API Keys (in .env)
- **Anthropic**: configured ✓
- **Twilio**: configured ✓ (SID, token, phone +18888854780, also +13102998162, +14155821479)
- **ElevenLabs**: configured ✓
- **Discord**: configured ✓ (bot token present)
- **Google OAuth**: configured ✓ (credentials.json + token.json)
- **Zoom**: NOT configured (blank)
- **Recall.ai**: NOT configured (blank)

## GCP Project
- Project ID: `agents-arcuate` (numeric: 550730552191)
- Gmail API: ENABLED
- Google Drive API: ENABLED
- Google Docs API: ENABLED

## Railway Deployment
- Project ID: dac8716b-a213-4da5-a6c8-55c2bef98e96
- GitHub repo connected: pangal-nsgy/arcuate_agents
- Branch: claude/mcp-chrome-extension-BW3zj
- **Build FAILED** — needs debugging next session
- Env vars to set: ANTHROPIC_API_KEY, TWILIO_*, ELEVENLABS_API_KEY, DISCORD_BOT_TOKEN, CHIEF_EMAIL, FOUNDER_PHONE_NUMBERS, MESSAGING_CHANNEL, CHROMA_PERSIST_DIR, SQLITE_DB_PATH, PORT, GOOGLE_TOKEN_JSON

## How to Run Locally
```bash
cd /Users/dhirajpangal/Desktop/arcuate_agents
source venv/bin/activate
PYTHONPATH=src python -m uvicorn chief_of_staff.main:app --host 0.0.0.0 --port 8000
```

## Next Steps (priority order)
1. **Fix Railway build** — debug the Dockerfile failure, get deployed off Dhiraj's machine
2. **Improve agent quality** — test with real questions, tune system prompt
3. **Add more knowledge sources** — Zoom meetings when credentials are available
4. **Set up chief@arcuate.health** — dedicated Google Workspace email for the agent

## Key Decisions Made
- Discord over SMS/WhatsApp — Twilio SMS wasn't delivering, Discord was instant to set up
- Railway over GCP VM — simpler deployment, connects to GitHub
- ChromaDB for vector search — local, no external service needed
- SQLite for metadata — simple, portable, no setup
- Background scheduler uses thread pool (run_in_executor) to avoid blocking the async event loop
- Google auth supports both file-based (local) and env var (GOOGLE_TOKEN_JSON) for cloud deployment

## Known Issues
- Anthropic rate limits hit on heavy queries — need to handle 429s gracefully or upgrade API tier
- ngrok has a stale session on electroballistic-celine-examinable.ngrok-free.dev — don't touch it, it's running existing Twilio stuff
- macOS Python needs SSL_CERT_FILE set via certifi (handled in startup code)
