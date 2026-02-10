"""FastAPI application — entry point for the Chief of Staff agent."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from chief_of_staff.config import settings
from chief_of_staff.knowledge.database import init_db
from chief_of_staff.webhooks.twilio import router as twilio_router
from chief_of_staff.webhooks.gmail import router as gmail_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info("Starting Arcuate Chief of Staff Agent...")
    init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down Chief of Staff Agent")


app = FastAPI(
    title="Arcuate Chief of Staff",
    description="AI Chief of Staff for Arcuate Health — unified knowledge + communication agent",
    version="0.1.0",
    lifespan=lifespan,
)

# Register webhook routers
app.include_router(twilio_router)
app.include_router(gmail_router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "agent": "chief_of_staff"}


@app.post("/api/ask")
async def ask_agent(query: str, founder_phone: str | None = None):
    """Direct API endpoint to ask the Chief of Staff a question.

    Useful for testing and for the web dashboard (future).
    """
    from chief_of_staff.agent.core import get_agent

    agent = get_agent()
    response = await agent.respond(
        user_message=query,
        founder_phone=founder_phone,
    )
    return {"response": response}


@app.post("/api/ingest/emails")
async def trigger_email_ingestion(max_results: int = 100, query: str = ""):
    """Manually trigger email ingestion."""
    from chief_of_staff.ingestion.gmail import fetch_and_ingest_emails

    count = fetch_and_ingest_emails(max_results=max_results, query=query)
    return {"emails_ingested": count}


@app.post("/api/ingest/docs")
async def trigger_docs_ingestion(folder_id: str | None = None, max_results: int = 50):
    """Manually trigger Google Docs ingestion."""
    from chief_of_staff.ingestion.gdocs import fetch_and_ingest_docs

    count = fetch_and_ingest_docs(folder_id=folder_id, max_results=max_results)
    return {"docs_ingested": count}


@app.post("/api/ingest/transcripts")
async def trigger_transcript_ingestion(limit: int = 50):
    """Manually trigger ElevenLabs transcript ingestion."""
    from chief_of_staff.ingestion.elevenlabs import fetch_and_ingest_transcripts

    count = await fetch_and_ingest_transcripts(limit=limit)
    return {"transcripts_ingested": count}


@app.post("/api/ingest/meeting")
async def ingest_meeting(
    title: str,
    transcript: str,
    meeting_date: str | None = None,
    attendees: list[str] | None = None,
    platform: str = "zoom",
):
    """Manually ingest a meeting transcript."""
    from chief_of_staff.ingestion.meetings import ingest_meeting_transcript

    doc_id = ingest_meeting_transcript(
        title=title,
        transcript=transcript,
        meeting_date=meeting_date,
        attendees=attendees,
        platform=platform,
    )
    return {"doc_id": doc_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
