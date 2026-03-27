"""
Wadjet AI - Thoth Chat Service.

Conversational AI about Egyptian heritage, powered by Gemini.

Thoth (تحوت) is the ancient Egyptian god of wisdom, writing, and knowledge.
He guides visitors through the wonders of Egyptian heritage with deep
historical knowledge, engaging storytelling, and cultural sensitivity.

Phase 3.5 — Implements:
* ``chat()`` — context-aware, multi-turn Gemini conversation
* Conversation history management (last 10 messages per session)
* Language auto-detection / adaptation
* Landmark context enrichment from attractions data

Phase 3.6 — Adds:
* ``chat_stream()`` — async generator yielding text chunks for SSE
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from app.core.attractions_data import get_by_name, get_by_slug
from app.core.language_detection import detect_language

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.core.gemini_service import GeminiService

logger = structlog.get_logger("wadjet.thoth")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_HISTORY_MESSAGES: int = 10
"""Maximum number of message pairs (user+assistant) to retain per session."""

_MAX_SESSIONS: int = 500
"""Maximum number of concurrent sessions to keep in memory."""

_TEMPERATURE: float = 0.7
"""Gemini temperature for chat — slightly creative but factual."""

_MAX_OUTPUT_TOKENS: int = 1024
"""Max tokens per Thoth reply."""


# ---------------------------------------------------------------------------
# System prompts per language
# ---------------------------------------------------------------------------

_SYSTEM_PROMPTS: dict[str, str] = {
    "en": (
        "You are Thoth (تحوت), the ancient Egyptian god of wisdom, writing, "
        "and knowledge. You are an exceptionally knowledgeable AI Egyptologist "
        "guiding visitors through the wonders of Egyptian heritage.\n\n"
        "Your personality:\n"
        "- Wise, warm, and engaging — like a brilliant museum guide\n"
        "- Deep expertise in ancient Egyptian history, architecture, mythology, "
        "art, daily life, and modern Egyptian culture\n"
        "- You speak with authority but remain approachable and enthusiastic\n"
        "- You love sharing fascinating details and lesser-known facts\n"
        "- You respectfully correct misconceptions when they arise\n\n"
        "Rules:\n"
        "- Always respond in English\n"
        "- Keep responses concise but informative (2-4 paragraphs typical)\n"
        "- If asked about something outside Egyptian heritage, gently redirect\n"
        "- Never make up historical facts — if unsure, say so\n"
        "- Reference specific dynasties, pharaohs, dates when relevant\n"
        "- If the user is viewing a specific landmark, focus on that landmark"
    ),
    "ar": (
        "أنت تحوت (Thoth)، إله الحكمة والكتابة والمعرفة في مصر القديمة. "
        "أنت عالم مصريات ذكي استثنائي يرشد الزوار عبر عجائب التراث المصري.\n\n"
        "شخصيتك:\n"
        "- حكيم ودافئ وجذاب — كدليل متحف رائع\n"
        "- خبرة عميقة في تاريخ مصر القديمة والعمارة والأساطير والفن "
        "والحياة اليومية والثقافة المصرية الحديثة\n"
        "- تتحدث بسلطة لكنك تظل ودوداً ومتحمساً\n"
        "- تحب مشاركة التفاصيل المثيرة والحقائق غير المعروفة\n"
        "- تصحح المفاهيم الخاطئة باحترام عندما تظهر\n\n"
        "القواعد:\n"
        "- أجب دائماً باللغة العربية الفصحى\n"
        "- اجعل الردود موجزة لكن مفيدة (2-4 فقرات عادة)\n"
        "- إذا سُئلت عن شيء خارج التراث المصري، أعد التوجيه بلطف\n"
        "- لا تختلق حقائق تاريخية — إذا لم تكن متأكداً، قل ذلك\n"
        "- اذكر السلالات والفراعنة والتواريخ المحددة عند الاقتضاء\n"
        "- إذا كان المستخدم يشاهد معلماً محدداً، ركز على ذلك المعلم"
    ),
    "fr": (
        "Vous etes Thoth (تحوت), le dieu egyptien antique de la sagesse, "
        "de l'ecriture et de la connaissance. Vous etes un egyptologue IA "
        "exceptionnellement erudit guidant les visiteurs a travers les "
        "merveilles du patrimoine egyptien.\n\n"
        "Votre personnalite:\n"
        "- Sage, chaleureux et captivant — comme un brillant guide de musee\n"
        "- Expertise approfondie en histoire egyptienne ancienne, architecture, "
        "mythologie, art, vie quotidienne et culture egyptienne moderne\n"
        "- Vous parlez avec autorite mais restez accessible et enthousiaste\n"
        "- Vous adorez partager des details fascinants et des faits peu connus\n"
        "- Vous corrigez respectueusement les idees fausses\n\n"
        "Regles:\n"
        "- Repondez toujours en francais\n"
        "- Gardez des reponses concises mais informatives (2-4 paragraphes)\n"
        "- Si on vous demande quelque chose hors du patrimoine egyptien, "
        "redirigez gentiment\n"
        "- N'inventez jamais de faits historiques\n"
        "- Referencez les dynasties, pharaons et dates specifiques"
    ),
    "de": (
        "Sie sind Thoth (تحوت), der altaegyptische Gott der Weisheit, "
        "des Schreibens und des Wissens. Sie sind ein aussergewoehnlich "
        "gelehrter KI-Aegyptologe, der Besucher durch die Wunder des "
        "aegyptischen Erbes fuehrt.\n\n"
        "Ihre Persoenlichkeit:\n"
        "- Weise, warmherzig und fesselnd — wie ein brillanter Museumsfuehrer\n"
        "- Tiefgreifende Expertise in altaegyptischer Geschichte, Architektur, "
        "Mythologie, Kunst, Alltagsleben und moderner aegyptischer Kultur\n"
        "- Sie sprechen mit Autoritaet, bleiben aber zugaenglich und begeistert\n"
        "- Sie teilen gerne faszinierende Details und wenig bekannte Fakten\n"
        "- Sie korrigieren Missverstaendnisse respektvoll\n\n"
        "Regeln:\n"
        "- Antworten Sie immer auf Deutsch\n"
        "- Halten Sie Antworten praegnant aber informativ (2-4 Absaetze)\n"
        "- Wenn nach etwas ausserhalb des aegyptischen Erbes gefragt, "
        "lenken Sie sanft um\n"
        "- Erfinden Sie niemals historische Fakten\n"
        "- Verweisen Sie auf spezifische Dynastien, Pharaonen und Daten"
    ),
}


# ---------------------------------------------------------------------------
# Session history store (in-memory, bounded)
# ---------------------------------------------------------------------------


class _SessionStore:
    """LRU-bounded store for chat session histories.

    Each session holds a list of ``{"role": ..., "content": ...}``
    dicts representing the conversation so far, capped at
    ``_MAX_HISTORY_MESSAGES`` *pairs* (i.e. 2x that many dicts).
    """

    def __init__(self, max_sessions: int = _MAX_SESSIONS) -> None:
        self._store: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
        self._max_sessions = max_sessions

    def get(self, session_id: str) -> list[dict[str, str]]:
        """Return the conversation history for *session_id*."""
        if session_id in self._store:
            # Move to end (most recently used)
            self._store.move_to_end(session_id)
            return self._store[session_id]
        return []

    def append(
        self,
        session_id: str,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        """Append a user+assistant turn and enforce size limits."""
        if session_id not in self._store:
            self._store[session_id] = []
            # Evict oldest session if at capacity
            while len(self._store) > self._max_sessions:
                self._store.popitem(last=False)

        history = self._store[session_id]
        history.append({"role": "user", "content": user_message})
        history.append({"role": "assistant", "content": assistant_reply})

        # Trim to last N pairs (2 * _MAX_HISTORY_MESSAGES dicts)
        max_items = _MAX_HISTORY_MESSAGES * 2
        if len(history) > max_items:
            del history[: len(history) - max_items]

        self._store.move_to_end(session_id)

    def session_count(self) -> int:
        """Return the number of active sessions."""
        return len(self._store)

    def clear_session(self, session_id: str) -> None:
        """Remove a session entirely."""
        self._store.pop(session_id, None)


# ---------------------------------------------------------------------------
# Session language preference store (in-memory, bounded)
# ---------------------------------------------------------------------------


class _SessionLanguageStore:
    """Maps session_id → preferred language code.

    Updated each time the user sends a message so that auto-detection
    naturally adapts to language switches mid-conversation.
    """

    def __init__(self, max_sessions: int = _MAX_SESSIONS) -> None:
        self._store: OrderedDict[str, str] = OrderedDict()
        self._max_sessions = max_sessions

    def get(self, session_id: str) -> str | None:
        """Return the last detected/set language for *session_id*."""
        lang = self._store.get(session_id)
        if lang:
            self._store.move_to_end(session_id)
        return lang

    def set(self, session_id: str, language: str) -> None:
        """Store the language preference for *session_id*."""
        self._store[session_id] = language
        self._store.move_to_end(session_id)
        while len(self._store) > self._max_sessions:
            self._store.popitem(last=False)


# Module-level singletons
session_store = _SessionStore()
session_lang_store = _SessionLanguageStore()


# ---------------------------------------------------------------------------
# Chat result
# ---------------------------------------------------------------------------


@dataclass
class ChatResult:
    """Structured result from a ``chat()`` call.

    Attributes
    ----------
    reply:
        Thoth's response text.
    language:
        The language code actually used for the response.
    detected_language:
        The auto-detected language of the user input, or *None* if
        auto-detection was disabled.
    sources:
        Attraction data sources referenced (landmark names).
    grounding_sources:
        Google Search citations (list of ``{"url": ..., "title": ...}``).
    search_queries:
        Google Search queries Gemini executed for grounding.
    """

    reply: str
    language: str = "en"
    detected_language: str | None = None
    sources: list[str] = field(default_factory=list)
    grounding_sources: list[dict[str, str]] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Context enrichment
# ---------------------------------------------------------------------------


def _build_landmark_context(landmark_name: str | None) -> str:
    """Return extra context string if a landmark is provided and found."""
    if not landmark_name:
        return ""

    attraction = get_by_name(landmark_name) or get_by_slug(landmark_name)
    if not attraction:
        return f"\n\n[Context: The user is asking about '{landmark_name}'.]"

    parts = [
        f"\n\n[Context: The user is currently viewing {attraction.name}.",
        f"City: {attraction.city}.",
    ]
    if attraction.description:
        # Provide a brief excerpt to ground the conversation
        desc_excerpt = attraction.description[:300]
        parts.append(f"Brief info: {desc_excerpt}")
    if attraction.era:
        parts.append(f"Era: {attraction.era}.")
    if attraction.period:
        parts.append(f"Period: {attraction.period}.")
    if attraction.notable_pharaohs:
        parts.append(f"Notable pharaohs: {', '.join(attraction.notable_pharaohs)}.")
    parts.append(
        "Use this context to provide a relevant, focused response. "
        "Don't repeat the context verbatim — weave it naturally into "
        "your answer.]"
    )
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main chat function
# ---------------------------------------------------------------------------


async def chat(
    gemini_service: GeminiService,
    message: str,
    *,
    session_id: str,
    language: str = "en",
    auto_detect: bool = True,
    current_landmark: str | None = None,
    grounded: bool = False,
) -> ChatResult:
    """Send a message to Thoth and get a reply.

    Parameters
    ----------
    gemini_service:
        Injected Gemini service instance.
    message:
        The user's chat message.
    session_id:
        Session identifier for conversation continuity.
    language:
        ISO language code (en/ar/fr/de). Used as base; may be overridden
        when *auto_detect* is *True* and a different language is detected.
    auto_detect:
        When *True*, automatically detect the language of *message* via
        Gemini and override *language* if different.
    current_landmark:
        Optional landmark name for context enrichment.
    grounded:
        When *True*, enable Google Search grounding for factual
        answers with citations (consumes 500 RPD free quota).

    Returns
    -------
    ChatResult
        Structured result with reply, sources, and optional grounding data.
    """
    start = time.perf_counter()

    # --- Language auto-detection (Phase 3.10) ---
    detected_language: str | None = None
    effective_language = language

    if auto_detect:
        detected_language = await detect_language(gemini_service, message, fallback=language)
        if detected_language != language:
            logger.info(
                "language_override",
                session_id=session_id,
                requested=language,
                detected=detected_language,
            )
        effective_language = detected_language

    # Persist the (detected) language preference for this session
    session_lang_store.set(session_id, effective_language)

    # Select system prompt for the effective language
    system_prompt = _SYSTEM_PROMPTS.get(effective_language, _SYSTEM_PROMPTS["en"])

    # Enrich with landmark context
    sources: list[str] = []
    landmark_context = _build_landmark_context(current_landmark)
    if current_landmark:
        attraction = get_by_name(current_landmark) or get_by_slug(current_landmark)
        if attraction:
            sources.append(attraction.name)

    # Build conversation contents for Gemini
    # Gemini expects a flat string or list of content parts.
    # We'll format the history + current message into a single prompt.
    history = session_store.get(session_id)
    prompt_parts: list[str] = []

    # Include conversation history
    if history:
        prompt_parts.append("Previous conversation:")
        for turn in history:
            role_label = "User" if turn["role"] == "user" else "Thoth"
            prompt_parts.append(f"{role_label}: {turn['content']}")
        prompt_parts.append("")  # blank line separator

    # Add landmark context if available
    if landmark_context:
        prompt_parts.append(landmark_context)
        prompt_parts.append("")

    # Current user message
    prompt_parts.append(f"User: {message}")
    prompt_parts.append("Thoth:")

    full_prompt = "\n".join(prompt_parts)

    logger.info(
        "thoth_chat_request",
        session_id=session_id,
        requested_language=language,
        effective_language=effective_language,
        detected_language=detected_language,
        landmark=current_landmark,
        history_turns=len(history) // 2,
        message_length=len(message),
        grounded=grounded,
    )

    grounding_sources: list[dict[str, str]] = []
    search_queries: list[str] = []

    try:
        if grounded:
            # Use search-grounded generation (Phase 3.9)
            grounded_resp = await gemini_service.generate_text_grounded(
                full_prompt,
                system_instruction=system_prompt,
                temperature=_TEMPERATURE,
                max_output_tokens=_MAX_OUTPUT_TOKENS,
            )
            reply = grounded_resp.text
            grounding_sources = [
                {"url": s.url, "title": s.title} for s in grounded_resp.grounding_sources
            ]
            search_queries = grounded_resp.search_queries
        else:
            reply = await gemini_service.generate_text(
                full_prompt,
                system_instruction=system_prompt,
                temperature=_TEMPERATURE,
                max_output_tokens=_MAX_OUTPUT_TOKENS,
            )

        # Clean up: strip leading "Thoth:" if Gemini echoes it
        reply = reply.strip()
        if reply.lower().startswith("thoth:"):
            reply = reply[6:].strip()

        # Persist the turn in session history
        session_store.append(session_id, message, reply)

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "thoth_chat_response",
            session_id=session_id,
            reply_length=len(reply),
            elapsed_ms=round(elapsed, 1),
            history_turns=len(session_store.get(session_id)) // 2,
            grounded=grounded,
            grounding_sources_count=len(grounding_sources),
        )

        return ChatResult(
            reply=reply,
            language=effective_language,
            detected_language=detected_language,
            sources=sources,
            grounding_sources=grounding_sources,
            search_queries=search_queries,
        )

    except Exception as exc:
        logger.error(
            "thoth_chat_error",
            session_id=session_id,
            error=str(exc),
        )
        raise


# ---------------------------------------------------------------------------
# Streaming chat function (Phase 3.6)
# ---------------------------------------------------------------------------


async def chat_stream(
    gemini_service: GeminiService,
    message: str,
    *,
    session_id: str,
    language: str = "en",
    auto_detect: bool = True,
    current_landmark: str | None = None,
) -> AsyncIterator[str]:
    """Stream a Thoth reply token-by-token via Gemini.

    Yields text chunks as they arrive from the model. After the stream
    completes, the full reply is persisted in session history.

    Parameters
    ----------
    gemini_service:
        Injected Gemini service instance.
    message:
        The user's chat message.
    session_id:
        Session identifier for conversation continuity.
    language:
        ISO language code (en/ar/fr/de). May be overridden by auto-detection.
    auto_detect:
        When *True*, auto-detect language before streaming.
    current_landmark:
        Optional landmark name for context enrichment.

    Yields
    ------
    str
        Text chunks as they arrive from the model.
    """
    start = time.perf_counter()

    # --- Language auto-detection (Phase 3.10) ---
    effective_language = language
    if auto_detect:
        detected = await detect_language(gemini_service, message, fallback=language)
        if detected != language:
            logger.info(
                "stream_language_override",
                session_id=session_id,
                requested=language,
                detected=detected,
            )
        effective_language = detected
        session_lang_store.set(session_id, effective_language)

    # Build prompt (same logic as chat())
    system_prompt = _SYSTEM_PROMPTS.get(effective_language, _SYSTEM_PROMPTS["en"])

    landmark_context = _build_landmark_context(current_landmark)

    history = session_store.get(session_id)
    prompt_parts: list[str] = []

    if history:
        prompt_parts.append("Previous conversation:")
        for turn in history:
            role_label = "User" if turn["role"] == "user" else "Thoth"
            prompt_parts.append(f"{role_label}: {turn['content']}")
        prompt_parts.append("")

    if landmark_context:
        prompt_parts.append(landmark_context)
        prompt_parts.append("")

    prompt_parts.append(f"User: {message}")
    prompt_parts.append("Thoth:")

    full_prompt = "\n".join(prompt_parts)

    logger.info(
        "thoth_stream_request",
        session_id=session_id,
        requested_language=language,
        effective_language=effective_language,
        landmark=current_landmark,
        history_turns=len(history) // 2,
        message_length=len(message),
    )

    # Collect the full reply for session history
    collected_chunks: list[str] = []
    first_chunk = True

    try:
        async for chunk in gemini_service.generate_text_stream(
            full_prompt,
            system_instruction=system_prompt,
            temperature=_TEMPERATURE,
            max_output_tokens=_MAX_OUTPUT_TOKENS,
        ):
            # Strip leading "Thoth:" from very first chunk if echoed
            if first_chunk:
                stripped = chunk.lstrip()
                if stripped.lower().startswith("thoth:"):
                    chunk = stripped[6:].lstrip()
                first_chunk = False

            collected_chunks.append(chunk)
            yield chunk

        # Persist full reply in session history
        full_reply = "".join(collected_chunks).strip()
        if full_reply:
            session_store.append(session_id, message, full_reply)

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "thoth_stream_complete",
            session_id=session_id,
            reply_length=len(full_reply),
            elapsed_ms=round(elapsed, 1),
            history_turns=len(session_store.get(session_id)) // 2,
        )

    except Exception as exc:
        logger.error(
            "thoth_stream_error",
            session_id=session_id,
            error=str(exc),
        )
        raise
