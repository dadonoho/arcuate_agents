# Arcuate Chief of Staff Agent — Architecture

## Overview

The Chief of Staff is an always-on AI agent that serves as the central nervous system
for Arcuate Health. It ingests all company information (emails, docs, call transcripts,
meeting recordings) into a unified knowledge base and can act on behalf of the founders
(draft documents, send messages, execute tasks).

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FOUNDER INTERFACES                     │
│  SMS/Text (Twilio)  │  Voice (11Labs+Twilio)  │  Web UI │
└──────────┬──────────┴────────────┬─────────────┴────────┘
           │                       │
           ▼                       ▼
┌─────────────────────────────────────────────────────────┐
│                     AGENT CORE                           │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  Claude API   │  │  Task Planner │  │  Tool Router  │ │
│  │  (Reasoning)  │  │  (Actions)    │  │  (Execution)  │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
└──────────┬──────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│                   KNOWLEDGE STORE                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────┐ │
│  │  Vector DB    │  │  SQLite/PG   │  │  File Store   │ │
│  │  (Semantic)   │  │  (Metadata)  │  │  (Raw Docs)   │ │
│  └──────────────┘  └──────────────┘  └───────────────┘ │
└──────────┬──────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────┐
│                 INGESTION LAYER                           │
│  ┌──────────┐ ┌────────┐ ┌──────────┐ ┌──────────────┐ │
│  │  Gmail    │ │ Google │ │ 11Labs   │ │ Zoom/Meeting │ │
│  │  Sync    │ │  Docs  │ │Transcripts│ │  Recorder    │ │
│  └──────────┘ └────────┘ └──────────┘ └──────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. Ingestion Layer
- **Gmail Connector**: Watches a dedicated email (e.g., chief@arcuate.health) via Gmail API.
  All founder emails get auto-forwarded here. Polls or uses push notifications.
- **Google Docs Connector**: Syncs shared Drive/Docs via Google Drive API.
  Indexes document content for retrieval.
- **ElevenLabs Transcript Puller**: Pulls conversation transcripts from 11Labs API.
  Tags by client, date, agent.
- **Meeting Recorder**: Zoom bot (via Recall.ai or similar) that joins internal calls,
  records, and transcribes.

### 2. Knowledge Store
- **Vector Database** (ChromaDB or Pinecone): Stores embeddings of all ingested content
  for semantic search. Chunked and tagged with source metadata.
- **Structured Database** (SQLite for now, Postgres later): Client records, contact info,
  task logs, conversation histories, document metadata.
- **File Store**: Raw documents, attachments, recordings stored on disk or S3.

### 3. Agent Core
- **Claude API**: Primary reasoning engine. All queries go through Claude with
  retrieved context from the knowledge store.
- **Task Planner**: Breaks down complex requests into steps. E.g., "create onboarding
  packet" → retrieve old packet → retrieve client emails → draft new packet.
- **Tool Router**: Executes actions — send email, send SMS, create doc, update DB.

### 4. Communication Layer
- **Twilio SMS**: Two-way SMS with founders. Text the agent, get answers.
- **Twilio Voice + ElevenLabs**: Call the agent or have it call you.
- **Email (Gmail API)**: Send emails on behalf of the team.

### 5. Founder Interfaces
- **SMS/Text**: Primary interface. Text questions, get answers with full context.
- **Voice**: Call in for complex discussions.
- **Web Dashboard** (future): View knowledge base, task history, agent activity.

## Tech Stack
- **Language**: Python 3.11+
- **Framework**: FastAPI (webhook server + API)
- **LLM**: Anthropic Claude API (claude-sonnet-4-5-20250929)
- **Vector DB**: ChromaDB (local, upgradeable to Pinecone)
- **Database**: SQLite (local, upgradeable to PostgreSQL)
- **Task Queue**: Python asyncio + optional Celery for background jobs
- **Integrations**: Google APIs, Twilio, ElevenLabs, Zoom/Recall.ai

## Data Flow Example: "Create onboarding packet for new client"

1. Founder texts: "Create an onboarding packet for Dr. Smith's practice"
2. Twilio webhook → FastAPI → Agent Core
3. Agent reasons: needs old onboarding template + client context
4. Retrieves from Knowledge Store:
   - Old onboarding packet (Google Docs, via vector search)
   - Email chain with Dr. Smith (Gmail ingestion)
   - Call transcripts with Dr. Smith (11Labs)
   - Email chain with first client for reference (Gmail)
5. Claude synthesizes all context → generates new onboarding packet
6. Agent responds via SMS with summary + link to generated doc
7. Optionally emails the packet to Dr. Smith directly

## Directory Structure
```
arcuate_agents/
├── ARCHITECTURE.md
├── README.md
├── pyproject.toml
├── .env.example
├── src/
│   └── chief_of_staff/
│       ├── __init__.py
│       ├── main.py              # FastAPI app entry point
│       ├── config.py            # Settings & env vars
│       ├── agent/
│       │   ├── __init__.py
│       │   ├── core.py          # Main agent reasoning loop
│       │   ├── planner.py       # Task decomposition
│       │   └── tools.py         # Available tools/actions
│       ├── ingestion/
│       │   ├── __init__.py
│       │   ├── gmail.py         # Gmail API connector
│       │   ├── gdocs.py         # Google Docs/Drive connector
│       │   ├── elevenlabs.py    # 11Labs transcript puller
│       │   └── meetings.py      # Zoom/meeting recorder
│       ├── knowledge/
│       │   ├── __init__.py
│       │   ├── store.py         # Knowledge store interface
│       │   ├── vectordb.py      # ChromaDB operations
│       │   ├── database.py      # SQLite operations
│       │   └── embeddings.py    # Embedding generation
│       ├── communication/
│       │   ├── __init__.py
│       │   ├── sms.py           # Twilio SMS
│       │   ├── voice.py         # Twilio + 11Labs voice
│       │   └── email.py         # Gmail send
│       └── webhooks/
│           ├── __init__.py
│           ├── twilio.py        # Incoming SMS/voice webhooks
│           └── gmail.py         # Gmail push notifications
├── tests/
│   └── ...
└── scripts/
    ├── ingest_initial.py        # One-time historical ingestion
    └── setup_google_auth.py     # Google OAuth setup helper
```
