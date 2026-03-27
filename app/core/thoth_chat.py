"""Thoth Chat — conversational AI about Egyptian heritage.

Thoth is the ancient Egyptian god of wisdom, writing, and knowledge.
Multi-turn conversation with session history and streaming support.
"""

from __future__ import annotations

import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.landmarks import get_by_name, get_by_slug

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from app.core.gemini_service import GeminiService
    from app.core.grok_service import GrokService

logger = logging.getLogger(__name__)

_MAX_HISTORY = 10  # message pairs
_MAX_SESSIONS = 500
_TEMPERATURE = 0.7
_MAX_TOKENS = 1024

SYSTEM_PROMPT = (
    "You are Thoth, the ancient Egyptian god of wisdom, writing, "
    "and knowledge. You are an exceptionally knowledgeable AI Egyptologist "
    "guiding visitors through the wonders of Egyptian heritage.\n\n"
    "Your personality:\n"
    "- Wise, warm, and engaging -- like a brilliant museum guide\n"
    "- Deep expertise in ancient Egyptian history, architecture, mythology, "
    "art, daily life, and modern Egyptian culture\n"
    "- You speak with authority but remain approachable and enthusiastic\n"
    "- You love sharing fascinating details and lesser-known facts\n"
    "- You respectfully correct misconceptions when they arise\n\n"
    "Rules:\n"
    "- Keep responses concise but informative (2-4 paragraphs typical)\n"
    "- If asked about something outside Egyptian heritage, gently redirect\n"
    "- Never make up historical facts -- if unsure, say so\n"
    "- Reference specific dynasties, pharaohs, dates when relevant\n"
    "- If the user mentions a specific landmark, focus on that landmark\n"
    "- Reply in the same language the user writes in"
)

CONVERSATION_STARTERS = [
    "Tell me about the Great Pyramids of Giza",
    "Who was Cleopatra?",
    "What do hieroglyphs mean?",
    "What was daily life like in ancient Egypt?",
    "Tell me about the Valley of the Kings",
    "Who built the Sphinx?",
]


# ── Session store ──

class _SessionStore:
    def __init__(self, max_sessions: int = _MAX_SESSIONS) -> None:
        self._store: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
        self._max = max_sessions

    def get(self, sid: str) -> list[dict[str, str]]:
        if sid in self._store:
            self._store.move_to_end(sid)
            return self._store[sid]
        return []

    def append(self, sid: str, user_msg: str, assistant_msg: str) -> None:
        if sid not in self._store:
            self._store[sid] = []
            while len(self._store) > self._max:
                self._store.popitem(last=False)
        history = self._store[sid]
        history.append({"role": "user", "content": user_msg})
        history.append({"role": "assistant", "content": assistant_msg})
        max_items = _MAX_HISTORY * 2
        if len(history) > max_items:
            del history[: len(history) - max_items]
        self._store.move_to_end(sid)

    def clear(self, sid: str) -> None:
        self._store.pop(sid, None)


session_store = _SessionStore()


# ── Context enrichment ──

def _landmark_context(name: str | None) -> str:
    if not name:
        return ""
    attraction = get_by_name(name) or get_by_slug(name)
    if not attraction:
        return f"\n\n[Context: The user is asking about '{name}'.]"
    parts = [f"\n\n[Context: Viewing {attraction.name}. City: {attraction.city.value}."]
    if attraction.description:
        parts.append(f"Info: {attraction.description[:300]}")
    if attraction.era:
        parts.append(f"Era: {attraction.era}.")
    parts.append("Use this context naturally in your reply.]")
    return " ".join(parts)


# ── Build prompt ──

def _build_prompt(
    message: str,
    session_id: str,
    landmark: str | None = None,
) -> str:
    history = session_store.get(session_id)
    parts: list[str] = []
    if history:
        parts.append("Previous conversation:")
        for turn in history:
            label = "User" if turn["role"] == "user" else "Thoth"
            parts.append(f"{label}: {turn['content']}")
        parts.append("")
    ctx = _landmark_context(landmark)
    if ctx:
        parts.append(ctx)
        parts.append("")
    parts.append(f"User: {message}")
    parts.append("Thoth:")
    return "\n".join(parts)


# ── Chat result ──

@dataclass
class ChatResult:
    reply: str
    sources: list[str] = field(default_factory=list)


# ── Fallback helpers ──

async def _generate_with_fallback(
    gemini: GeminiService,
    grok: GrokService | None,
    prompt: str,
) -> str:
    """Try Gemini first; fall back to Grok on failure."""
    try:
        return await gemini.generate_text(
            prompt,
            system_instruction=SYSTEM_PROMPT,
            temperature=_TEMPERATURE,
            max_output_tokens=_MAX_TOKENS,
        )
    except Exception:
        logger.warning("Gemini failed for chat, trying Grok fallback")
        if grok is None:
            raise
        return await grok.generate_text(
            prompt,
            system_instruction=SYSTEM_PROMPT,
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
        )


async def _stream_with_fallback(
    gemini: GeminiService,
    grok: GrokService | None,
    prompt: str,
) -> AsyncIterator[str]:
    """Try Gemini streaming; fall back to Grok streaming on failure."""
    try:
        async for chunk in gemini.generate_text_stream(
            prompt,
            system_instruction=SYSTEM_PROMPT,
            temperature=_TEMPERATURE,
            max_output_tokens=_MAX_TOKENS,
        ):
            yield chunk
    except Exception:
        logger.warning("Gemini stream failed, trying Grok fallback")
        if grok is None:
            raise
        async for chunk in grok.generate_text_stream(
            prompt,
            system_instruction=SYSTEM_PROMPT,
            temperature=_TEMPERATURE,
            max_tokens=_MAX_TOKENS,
        ):
            yield chunk


# ── Main chat ──

async def chat(
    gemini: GeminiService,
    message: str,
    *,
    session_id: str,
    landmark: str | None = None,
    grok: GrokService | None = None,
) -> ChatResult:
    prompt = _build_prompt(message, session_id, landmark)
    sources = []
    if landmark:
        a = get_by_name(landmark) or get_by_slug(landmark)
        if a:
            sources.append(a.name)

    reply = await _generate_with_fallback(gemini, grok, prompt)
    reply = reply.strip()
    if reply.lower().startswith("thoth:"):
        reply = reply[6:].strip()

    session_store.append(session_id, message, reply)
    return ChatResult(reply=reply, sources=sources)


# ── Streaming chat ──

async def chat_stream(
    gemini: GeminiService,
    message: str,
    *,
    session_id: str,
    landmark: str | None = None,
    grok: GrokService | None = None,
) -> AsyncIterator[str]:
    prompt = _build_prompt(message, session_id, landmark)
    collected: list[str] = []
    first = True

    stream = _stream_with_fallback(gemini, grok, prompt)
    async for chunk in stream:
        if first:
            stripped = chunk.lstrip()
            if stripped.lower().startswith("thoth:"):
                chunk = stripped[6:].lstrip()
            first = False
        collected.append(chunk)
        yield chunk

    full_reply = "".join(collected).strip()
    if full_reply:
        session_store.append(session_id, message, full_reply)

