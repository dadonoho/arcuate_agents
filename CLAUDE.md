# Arcuate Chief of Staff Agent

## What This Is
AI Chief of Staff for Arcuate Health — a healthcare startup doing agentic outreach for aesthetic practices (ElevenLabs + Twilio voice calls to practices).
The agent ingests all company knowledge and lets founders interact via Discord. Now supports self-modification, persistent memory, sub-agent spawning, and a live dashboard.

## Architecture (as of 2026-02-14)

### Agent System
- **Config-driven agents** — each agent is defined in `agents/<name>.yaml` (system prompt, tools, permissions)
- **Self-modification** — agents can update their own standing instructions via `update_own_instructions` tool
- **Persistent memory** — per-agent memory files in `agent_memory/<name>.md`, survives restarts
- **Sub-agent spawning** — Chief of Staff can create specialized agents via `create_sub_agent` tool
- **Task delegation** — delegates tasks to sub-agents via `delegate_task` tool
- **Activity tracking** — every action logged to SQLite `agent_activity` table
- **Dashboard** — live web dashboard at `/dashboard` showing all agent activity

### Key Directories
```
agents/                  # Agent YAML configs (self-modifiable)
  chief_of_staff.yaml    # Main agent config
agent_memory/            # Persistent memory per agent
  chief_of_staff.md      # Learnings, preferences, facts
src/chief_of_staff/
  agent/
    core.py              # Agent loop (config-driven, activity-tracked)
    tools.py             # 12 tools including self-mod, memory, delegation
    activity.py          # Activity logging to SQLite
    memory.py            # Persistent memory read/write/search
    registry.py          # Agent config loading from YAML
    planner.py           # Multi-step task planner
  dashboard/
    routes.py            # Dashboard API + HTML frontend
  communication/         # Discord, SMS, email
  ingestion/             # Gmail, GDocs, ElevenLabs, Zoom
  knowledge/             # ChromaDB + SQLite
  webhooks/              # Twilio, Gmail push, Zoom, Recall.ai
```

### Tools (12 total)
| Tool | Category | Description |
|------|----------|-------------|
| search_knowledge | Knowledge | Semantic search across all company data |
| list_recent_emails | Knowledge | List emails from DB |
| search_meetings | Knowledge | Search meeting transcripts |
| send_sms | Communication | WhatsApp/SMS via Twilio |
| send_email | Communication | Gmail API |
| draft_document | Communication | Create draft docs |
| send_meeting_bot | Meetings | Dispatch Recall.ai bot |
| update_own_instructions | Self-Mod | Add/remove/replace standing instructions |
| remember | Memory | Store persistent learnings |
| recall_memory | Memory | Search persistent memory |
| create_sub_agent | Delegation | Create new agent from YAML config |
| delegate_task | Delegation | Send task to sub-agent, get result |

### Dashboard
- **URL**: `http://localhost:8000/dashboard`
- **Auto-refreshes** every 5 seconds
- **Shows**: stats cards, activity feed, agent list with standing instructions
- **Filters**: by agent, action type, time range
- **API endpoints**: `/dashboard/api/stats`, `/dashboard/api/activity`, `/dashboard/api/agents`

## Founders
- Dhiraj Pangal: +19256993247 (Discord: dhirajarcuate)
- 4 part-time founders total

## Current Status (as of 2026-02-14)
- **Discord bot is WORKING** — "Arcuate Chief of Staff#7949" (bot ID: 1471658651491106847)
- **Knowledge base loaded**: 501 emails, 27 Google Docs, 35 ElevenLabs transcripts
- **Agent system**: config-driven with self-modification, memory, and sub-agents
- **Dashboard**: live at /dashboard with real-time activity tracking
- **Railway deployment**: build failed — needs debugging (Dockerfile issue likely)
- **Local server**: works perfectly on localhost:8000
- **SMS via Twilio**: sends from API but Dhiraj says he doesn't receive texts — skip SMS, use Discord

## Communication Channel
**Discord** (primary). Bot responds to:
- DMs to the bot
- @mentions in any channel
- Messages in channels listed in DISCORD_CHANNELS config (default: chief-of-staff, arcuatechat)

## Data Sources
- **Gmail** — authenticated via OAuth (token.json present locally)
- **Google Docs** — same OAuth token, reads all docs in the account
- **ElevenLabs** — AI call transcripts (Conversational AI API)
- Zoom/Recall.ai — code built but credentials not configured

## Credentials & Local Files (all in repo root, all gitignored)
- `.env` — all API keys and config
- `credentials.json` — Google OAuth client (Desktop app type, project: agents-arcuate)
- `token.json` — Google OAuth refresh token (auto-refreshes)
- `chief_of_staff.db` — SQLite with document metadata + conversation history + activity tracking
- `chroma_data/` — ChromaDB vector embeddings (~33MB)

## API Keys (in .env)
- **Anthropic**: configured (claude-sonnet-4-5-20250929)
- **Twilio**: configured (SID, token, phone +18888854780, also +13102998162, +14155821479)
- **ElevenLabs**: configured
- **Discord**: configured (bot token present)
- **Google OAuth**: configured (credentials.json + token.json)
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
# Dashboard: http://localhost:8000/dashboard
```

## Next Steps (priority order)
1. **Fix Railway build** — debug the Dockerfile failure, get deployed off Dhiraj's machine
2. **Test agent self-modification** — verify standing instructions persist and improve quality
3. **Create first sub-agents** — lead_scorer, research_agent, etc. via Discord
4. **Add more knowledge sources** — Zoom meetings when credentials are available
5. **Set up chief@arcuate.health** — dedicated Google Workspace email for the agent

## Key Decisions Made
- Discord over SMS/WhatsApp — Twilio SMS wasn't delivering
- Config-driven agents over hardcoded — agents load from YAML, can self-modify
- Raw Anthropic API over Agent SDK — full control over tool loop, better activity tracking, cleaner security model
- File-based memory over DB — readable, git-trackable, simple
- SQLite for activity tracking — same DB, no new dependencies
- Railway over GCP VM — simpler deployment, connects to GitHub
- ChromaDB for vector search — local, no external service needed

## Known Issues
- Anthropic rate limits hit on heavy queries — need to handle 429s gracefully
- ngrok has a stale session — don't touch it, runs existing Twilio stuff
- macOS Python needs SSL_CERT_FILE set via certifi (handled in startup code)
