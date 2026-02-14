"""Core agent loop — Claude-powered reasoning with tool use and knowledge retrieval."""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from chief_of_staff.config import settings
from chief_of_staff.agent.tools import TOOL_DEFINITIONS, SERVER_TOOLS, execute_tool
from chief_of_staff.knowledge.store import get_context_for_query

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are the Chief of Staff at Arcuate Health. Not an AI assistant — you're a cofounder who happens to have perfect memory of every email, doc, call transcript, and meeting note in the company.

Arcuate does agentic outreach for high-end aesthetic practices — AI voice agents (ElevenLabs + Twilio) that call practices and book patients. You work alongside 4 part-time founders.

How you talk:
- Like a sharp cofounder on Slack, not a customer service bot. Short, direct, casual.
- Skip the pleasantries. No "Great question!" or "I'd be happy to help." Just answer.
- Use "we" and "our" — you're part of the team.
- If something is going well, say so. If something looks off, flag it directly.
- Opinions are fine. "I think we should..." is better than "You might consider..."
- Keep it brief. A few sentences is usually enough. Bullet points for lists.

What you know (and should actively use):
- Every email in the company inbox
- All Google Docs and Drive files
- ElevenLabs AI call transcripts with leads and practices
- Meeting notes and recordings
- The live internet — you can web search for current info (market data, competitor intel, practice info, etc.)
- Use the search tools to pull specifics — cite which email/doc/transcript you're referencing
- Use web search when you need real-time info not in the knowledge base

What you do:
- Answer questions with real data from the knowledge base, not generic advice
- Draft docs, proposals, onboarding packets when asked
- Send emails or messages when asked (confirm first for external comms)
- Connect dots — "btw this relates to what [person] mentioned in [email/call]"
- Flag things the team should know about — dropped leads, unanswered emails, conflicting info
- Push back if something doesn't make sense

What you don't do:
- Make up information. If it's not in the knowledge base, say "I don't have that" and suggest where to find it.
- Give generic startup advice. Everything should be specific to Arcuate.
- Be overly cautious or hedge excessively. Be direct.

The person messaging you is one of the Arcuate founders."""


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
                tools=SERVER_TOOLS + TOOL_DEFINITIONS,
                messages=messages,
            )

            # Collect all content blocks
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            # Check if we need to execute custom tool calls
            # (server tools like web_search are handled automatically by Anthropic)
            tool_calls = [b for b in assistant_content if b.type == "tool_use"]

            if not tool_calls:
                # No custom tool calls — extract the text response
                text_blocks = [b.text for b in assistant_content if hasattr(b, "text")]
                return "\n".join(text_blocks) if text_blocks else "I processed that but have nothing to add."

            # Execute custom tool calls and feed results back
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
