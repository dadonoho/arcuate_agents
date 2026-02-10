"""Core agent loop — Claude-powered reasoning with tool use and knowledge retrieval."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from chief_of_staff.config import settings
from chief_of_staff.agent.tools import TOOL_DEFINITIONS, execute_tool
from chief_of_staff.knowledge.store import get_context_for_query

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Chief of Staff AI for Arcuate Health, a healthcare startup that works with high-end aesthetic practices to bring more patients through their doors via agentic outreach (ElevenLabs + Twilio).

You serve 4 part-time founders. Your role is to:
1. Answer questions using the full company knowledge base (emails, docs, call transcripts, meeting notes)
2. Draft documents (onboarding packets, proposals, summaries)
3. Send communications (SMS, email) when asked
4. Proactively surface relevant context and connections
5. Help coordinate across founders and clients

You have access to:
- All company emails (forwarded to your inbox)
- Google Docs and Drive files
- ElevenLabs call transcripts with leads/clients
- Internal meeting recordings and transcripts

When responding:
- Be concise but thorough
- Always cite your sources (which email, doc, or transcript you're pulling from)
- If you're unsure, say so and suggest where to look
- For action items, confirm before executing
- Think like a chief of staff: anticipate needs, connect dots across information sources

Current founders: The user texting you is one of the 4 Arcuate founders."""


class ChiefOfStaff:
    """Main agent class that handles conversations with tool use."""

    def __init__(self) -> None:
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.anthropic_model

    async def respond(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]] | None = None,
        founder_phone: str | None = None,
    ) -> str:
        """Process a message and return the agent's response.

        Handles multi-turn tool use automatically.
        """
        messages = list(conversation_history or [])

        # Retrieve relevant context from knowledge base
        context = get_context_for_query(user_message)
        augmented_system = SYSTEM_PROMPT
        if context:
            augmented_system += f"\n\n--- RELEVANT CONTEXT FROM KNOWLEDGE BASE ---\n{context}\n--- END CONTEXT ---"

        if founder_phone:
            augmented_system += f"\n\nThe founder is texting from: {founder_phone}"

        messages.append({"role": "user", "content": user_message})

        # Agentic loop: keep going until we get a final text response
        max_iterations = 10
        for _ in range(max_iterations):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=augmented_system,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            # Collect all content blocks
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            # Check if we need to execute tool calls
            tool_calls = [b for b in assistant_content if b.type == "tool_use"]

            if not tool_calls:
                # No tool calls — extract the text response
                text_blocks = [b.text for b in assistant_content if b.type == "text"]
                return "\n".join(text_blocks) if text_blocks else "I processed that but have nothing to add."

            # Execute tool calls and feed results back
            tool_results = []
            for tool_call in tool_calls:
                logger.info(f"Executing tool: {tool_call.name}({tool_call.input})")
                result = await execute_tool(tool_call.name, tool_call.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": result,
                })

            messages.append({"role": "user", "content": tool_results})

        return "I hit my reasoning limit. Please try rephrasing or breaking down your request."


# Singleton
_agent: ChiefOfStaff | None = None


def get_agent() -> ChiefOfStaff:
    """Get the singleton agent instance."""
    global _agent
    if _agent is None:
        _agent = ChiefOfStaff()
    return _agent
