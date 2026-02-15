"""Tools available to agents — base tools + self-modification + memory + delegation."""

from __future__ import annotations

import json
import logging
from typing import Any

from chief_of_staff.knowledge import store as knowledge_store

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool definition catalog — each tool has a name, description, and schema
# ---------------------------------------------------------------------------

ALL_TOOL_DEFINITIONS: dict[str, dict[str, Any]] = {
    "search_knowledge": {
        "name": "search_knowledge",
        "description": "Search the company knowledge base (emails, docs, call transcripts, meeting notes).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "source_filter": {
                    "type": "string",
                    "enum": ["gmail", "gdocs", "elevenlabs", "meeting"],
                    "description": "Optionally filter by source type",
                },
            },
            "required": ["query"],
        },
    },
    "send_sms": {
        "name": "send_sms",
        "description": "Send a WhatsApp message or SMS to a phone number.",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Phone number in E.164 format (+1...)"},
                "message": {"type": "string", "description": "The message to send"},
            },
            "required": ["to", "message"],
        },
    },
    "send_email": {
        "name": "send_email",
        "description": "Send an email on behalf of the Chief of Staff.",
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
    "draft_document": {
        "name": "draft_document",
        "description": "Create a draft document (onboarding packet, proposal, summary, etc.).",
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
    "list_recent_emails": {
        "name": "list_recent_emails",
        "description": "List recent emails from the knowledge base.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term for emails"},
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
    },
    "search_meetings": {
        "name": "search_meetings",
        "description": "Search meeting transcripts (Zoom, Recall.ai bot transcripts).",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for meetings"},
                "limit": {"type": "integer", "description": "Max results (default 10)"},
            },
            "required": ["query"],
        },
    },
    "send_meeting_bot": {
        "name": "send_meeting_bot",
        "description": "Send a bot to join and record a Zoom/Google Meet/Teams meeting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "meeting_url": {"type": "string", "description": "The meeting join URL"},
                "meeting_title": {"type": "string", "description": "Optional title for the meeting"},
            },
            "required": ["meeting_url"],
        },
    },
    # --- Self-modification tools ---
    "update_own_instructions": {
        "name": "update_own_instructions",
        "description": "Update your own standing instructions. Use this when you learn recurring patterns, preferences, or rules that should persist across conversations. These instructions are injected into your system prompt on every message.",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove", "replace_all"],
                    "description": "add: append a new instruction. remove: remove by index. replace_all: replace all instructions.",
                },
                "instruction": {"type": "string", "description": "The instruction to add (for 'add' action)"},
                "index": {"type": "integer", "description": "Index to remove (for 'remove' action, 0-based)"},
                "instructions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Full list of instructions (for 'replace_all' action)",
                },
            },
            "required": ["action"],
        },
    },
    # --- Memory tools ---
    "remember": {
        "name": "remember",
        "description": "Store something in your persistent memory. Use for: key facts about people, decisions made, patterns noticed, things to follow up on. Memory persists across all conversations.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "What to remember"},
                "category": {
                    "type": "string",
                    "enum": ["person", "decision", "pattern", "follow_up", "preference", "general"],
                    "description": "Category for the memory entry",
                },
            },
            "required": ["content", "category"],
        },
    },
    "recall_memory": {
        "name": "recall_memory",
        "description": "Search your persistent memory for previously stored information.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to search for in memory"},
            },
            "required": ["query"],
        },
    },
    # --- Delegation tools ---
    "create_sub_agent": {
        "name": "create_sub_agent",
        "description": "Create a new specialized sub-agent. Use when a recurring task needs a dedicated agent with a focused system prompt and specific tools.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Agent name (snake_case, e.g., lead_scorer)"},
                "display_name": {"type": "string", "description": "Human-readable name"},
                "system_prompt": {"type": "string", "description": "System prompt for the sub-agent"},
                "tools": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tools the sub-agent can use",
                },
            },
            "required": ["name", "display_name", "system_prompt"],
        },
    },
    "delegate_task": {
        "name": "delegate_task",
        "description": "Delegate a task to a sub-agent. The sub-agent runs autonomously and returns a result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "agent_name": {"type": "string", "description": "Name of the sub-agent to delegate to"},
                "task": {"type": "string", "description": "The task to delegate"},
            },
            "required": ["agent_name", "task"],
        },
    },
}


def get_tool_definitions(tool_names: list[str]) -> list[dict[str, Any]]:
    """Get tool definitions for a specific set of tool names."""
    return [ALL_TOOL_DEFINITIONS[name] for name in tool_names if name in ALL_TOOL_DEFINITIONS]


def get_server_tools(server_tools_config: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Get server tool definitions from config."""
    return server_tools_config if server_tools_config else []


# ---------------------------------------------------------------------------
# Tool execution
# ---------------------------------------------------------------------------


async def execute_tool(name: str, args: dict[str, Any], agent_name: str = "chief_of_staff") -> str:
    """Execute a tool call and return the result as a string."""

    # --- Knowledge tools ---
    if name == "search_knowledge":
        from chief_of_staff.agent.activity import log_activity, KNOWLEDGE_SEARCH
        log_activity(
            agent_name=agent_name,
            action_type=KNOWLEDGE_SEARCH,
            action_detail=args["query"],
            input_summary=args.get("source_filter", "all"),
        )
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

    # --- Communication tools ---
    elif name == "send_sms":
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
            return "No meeting transcripts found."
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
        return f"Meeting bot dispatched (ID: {bot_id}). Will transcribe automatically."

    # --- Self-modification tools ---
    elif name == "update_own_instructions":
        from chief_of_staff.agent.activity import log_activity, CONFIG_UPDATE
        from chief_of_staff.agent.registry import get_registry

        registry = get_registry()
        config = registry.get(agent_name)
        if not config:
            return f"Error: agent '{agent_name}' not found."
        if not config.permissions.get("can_self_modify"):
            return "Error: this agent does not have permission to self-modify."

        action = args["action"]
        if action == "add":
            instruction = args.get("instruction", "")
            if not instruction:
                return "Error: 'instruction' required for add action."
            config.standing_instructions.append(instruction)
        elif action == "remove":
            idx = args.get("index", -1)
            if 0 <= idx < len(config.standing_instructions):
                removed = config.standing_instructions.pop(idx)
            else:
                return f"Error: invalid index {idx}. Current instructions count: {len(config.standing_instructions)}"
        elif action == "replace_all":
            config.standing_instructions = args.get("instructions", [])
        else:
            return f"Error: unknown action '{action}'"

        registry.update_agent_instructions(agent_name, config.standing_instructions)

        log_activity(
            agent_name=agent_name,
            action_type=CONFIG_UPDATE,
            action_detail=f"update_own_instructions: {action}",
            input_summary=str(args)[:500],
            output_summary=str(config.standing_instructions)[:500],
        )
        return f"Instructions updated. Current standing instructions ({len(config.standing_instructions)}):\n" + \
               "\n".join(f"  {i}. {inst}" for i, inst in enumerate(config.standing_instructions))

    # --- Memory tools ---
    elif name == "remember":
        from chief_of_staff.agent.activity import log_activity, MEMORY_WRITE
        from chief_of_staff.agent.memory import append_memory

        content = args["content"]
        category = args.get("category", "general")
        append_memory(agent_name, content, category)

        log_activity(
            agent_name=agent_name,
            action_type=MEMORY_WRITE,
            action_detail=f"[{category}] {content[:200]}",
        )
        return f"Remembered [{category}]: {content}"

    elif name == "recall_memory":
        from chief_of_staff.agent.activity import log_activity, MEMORY_READ
        from chief_of_staff.agent.memory import search_memory

        query = args["query"]
        results = search_memory(agent_name, query)

        log_activity(
            agent_name=agent_name,
            action_type=MEMORY_READ,
            action_detail=query,
            output_summary=f"{len(results)} entries found",
        )
        if not results:
            return "No matching memories found."
        return "\n---\n".join(results)

    # --- Delegation tools ---
    elif name == "create_sub_agent":
        from chief_of_staff.agent.activity import log_activity, SUB_AGENT_SPAWN
        from chief_of_staff.agent.registry import get_registry

        registry = get_registry()
        config = registry.get(agent_name)
        if config and not config.permissions.get("can_create_agents"):
            return "Error: this agent does not have permission to create sub-agents."

        new_agent = registry.create_agent(
            name=args["name"],
            display_name=args["display_name"],
            system_prompt=args["system_prompt"],
            tools=args.get("tools", ["search_knowledge"]),
        )

        log_activity(
            agent_name=agent_name,
            action_type=SUB_AGENT_SPAWN,
            action_detail=f"Created sub-agent: {new_agent.name}",
            metadata={"sub_agent": new_agent.name, "tools": new_agent.tools},
        )
        return f"Sub-agent '{new_agent.display_name}' created with tools: {new_agent.tools}"

    elif name == "delegate_task":
        from chief_of_staff.agent.activity import log_activity, DELEGATION
        from chief_of_staff.agent.core import get_sub_agent

        target_name = args["agent_name"]
        task = args["task"]

        sub_agent = get_sub_agent(target_name)
        if not sub_agent:
            return f"Error: sub-agent '{target_name}' not found."

        log_activity(
            agent_name=agent_name,
            action_type=DELEGATION,
            action_detail=f"Delegating to {target_name}",
            input_summary=task[:500],
        )

        try:
            result = await sub_agent.respond(
                user_message=task,
                channel="delegation",
                user_id=agent_name,
            )
            return f"[{target_name} response]:\n{result}"
        except Exception as e:
            return f"Error delegating to {target_name}: {e}"

    else:
        return f"Unknown tool: {name}"
