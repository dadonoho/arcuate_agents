"""Tools available to the Chief of Staff agent for taking actions."""

from __future__ import annotations

import json
from typing import Any

from chief_of_staff.knowledge import store as knowledge_store

# Tool definitions for Claude's tool_use API
TOOL_DEFINITIONS = [
    {
        "name": "search_knowledge",
        "description": "Search the company knowledge base (emails, docs, call transcripts, meeting notes) for relevant information. Use this to find context about clients, past conversations, documents, or any company information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query — be specific about what you're looking for",
                },
                "source_filter": {
                    "type": "string",
                    "enum": ["gmail", "gdocs", "elevenlabs", "meeting"],
                    "description": "Optionally filter to a specific source type",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "send_sms",
        "description": "Send a WhatsApp message (or SMS) to a phone number. Use this to communicate with founders or contacts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Phone number in E.164 format (+1...)"},
                "message": {"type": "string", "description": "The message to send"},
            },
            "required": ["to", "message"],
        },
    },
    {
        "name": "send_email",
        "description": "Send an email on behalf of the Chief of Staff. Use for formal communications, sending documents, or outreach.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body (plain text)"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "draft_document",
        "description": "Create a draft document (e.g., onboarding packet, proposal, summary). Returns the document content for review before sending.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Document title"},
                "content": {"type": "string", "description": "Full document content in markdown"},
                "doc_type": {
                    "type": "string",
                    "enum": ["onboarding_packet", "proposal", "summary", "memo", "other"],
                    "description": "Type of document",
                },
            },
            "required": ["title", "content", "doc_type"],
        },
    },
    {
        "name": "list_recent_emails",
        "description": "List recent emails from the knowledge base, optionally filtered by sender or subject.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term for emails"},
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_meetings",
        "description": "Search meeting transcripts (Zoom recordings, Recall.ai bot transcripts). Use this to find what was discussed in internal meetings.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query — topic, person name, or keyword from the meeting",
                },
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "send_meeting_bot",
        "description": "Send the Chief of Staff meeting bot to join and record a Zoom/Google Meet/Teams meeting. The bot will transcribe the meeting and ingest it into the knowledge base automatically.",
        "input_schema": {
            "type": "object",
            "properties": {
                "meeting_url": {
                    "type": "string",
                    "description": "The meeting join URL (e.g., https://zoom.us/j/123456)",
                },
                "meeting_title": {
                    "type": "string",
                    "description": "Optional title/description for the meeting",
                },
            },
            "required": ["meeting_url"],
        },
    },
]


async def execute_tool(name: str, args: dict[str, Any]) -> str:
    """Execute a tool call and return the result as a string."""
    if name == "search_knowledge":
        results = knowledge_store.search(
            query=args["query"],
            n_results=args.get("limit", 10),
            source_filter=args.get("source_filter"),
        )
        if not results:
            return "No results found."
        formatted = []
        for r in results:
            src = r["metadata"].get("source", "?")
            title = r["metadata"].get("title", "untitled")
            formatted.append(f"[{src}: {title}]\n{r['text'][:500]}")
        return "\n---\n".join(formatted)

    elif name == "send_sms":
        # Import here to avoid circular deps
        from chief_of_staff.communication.sms import send_sms
        result = await send_sms(to=args["to"], body=args["message"])
        return f"SMS sent to {args['to']}: {result}"

    elif name == "send_email":
        from chief_of_staff.communication.email import send_email
        result = await send_email(to=args["to"], subject=args["subject"], body=args["body"])
        return f"Email sent to {args['to']}: {result}"

    elif name == "draft_document":
        return json.dumps({
            "status": "draft_created",
            "title": args["title"],
            "type": args["doc_type"],
            "content": args["content"],
        })

    elif name == "list_recent_emails":
        from chief_of_staff.knowledge.database import search_documents
        docs = search_documents(query=args["query"], source="gmail", limit=args.get("limit", 10))
        if not docs:
            return "No emails found matching that query."
        return json.dumps(docs, indent=2, default=str)

    elif name == "search_meetings":
        results = knowledge_store.search(
            query=args["query"],
            n_results=args.get("limit", 10),
            source_filter="meeting",
        )
        if not results:
            return "No meeting transcripts found matching that query."
        formatted = []
        for r in results:
            title = r["metadata"].get("title", "untitled")
            platform = r["metadata"].get("platform", "unknown")
            formatted.append(f"[{platform}: {title}]\n{r['text'][:500]}")
        return "\n---\n".join(formatted)

    elif name == "send_meeting_bot":
        from chief_of_staff.ingestion.recall_bot import dispatch_bot
        result = await dispatch_bot(
            meeting_url=args["meeting_url"],
            meeting_title=args.get("meeting_title", ""),
        )
        bot_id = result.get("id", "unknown")
        return f"Meeting bot dispatched (ID: {bot_id}). It will join the meeting, record, and transcribe automatically. I'll notify you when the transcript is ready."

    else:
        return f"Unknown tool: {name}"
