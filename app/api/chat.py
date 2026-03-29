"""Chat API — Thoth AI chatbot endpoints.

POST /api/chat          — Send message, get JSON reply
POST /api/chat/stream   — SSE streaming response (POST for CSRF compat)
POST /api/chat/clear    — Clear conversation session
"""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_optional_user
from app.db.models import User
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=128)
    landmark: str | None = Field(default=None, max_length=200)


class StreamRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str = Field(..., min_length=1, max_length=128)
    landmark: str | None = Field(default=None, max_length=200)


class ClearRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)


def _get_gemini(request: Request):
    """Retrieve GeminiService from app state."""
    gemini = getattr(request.app.state, "gemini", None)
    if gemini is None:
        raise HTTPException(status_code=503, detail="AI service not available")
    return gemini


def _get_grok(request: Request):
    """Retrieve GrokService from app state (optional)."""
    return getattr(request.app.state, "grok", None)


def _get_groq(request: Request):
    """Retrieve GroqService from app state (optional)."""
    return getattr(request.app.state, "groq", None)


@router.post("")
@limiter.limit("30/minute")
async def chat_message(body: ChatRequest, request: Request):
    """Non-streaming chat — returns full reply as JSON."""
    from app.core.thoth_chat import chat

    gemini = _get_gemini(request)
    grok = _get_grok(request)
    groq = _get_groq(request)
    try:
        result = await chat(
            gemini,
            body.message,
            session_id=body.session_id,
            landmark=body.landmark,
            grok=grok,
            groq=groq,
        )
        return JSONResponse(content={
            "reply": result.reply,
            "sources": result.sources,
        })
    except Exception:
        logger.exception("Chat error")
        raise HTTPException(status_code=500, detail="Failed to generate response")


@router.post("/stream")
@limiter.limit("30/minute")
async def chat_stream(
    body: StreamRequest,
    request: Request,
):
    """SSE streaming chat — sends text chunks as Server-Sent Events."""
    from app.core.thoth_chat import chat_stream as _chat_stream

    gemini = _get_gemini(request)
    grok = _get_grok(request)
    groq = _get_groq(request)

    async def event_generator():
        try:
            async for chunk in _chat_stream(
                gemini,
                body.message,
                session_id=body.session_id,
                landmark=body.landmark,
                grok=grok,
                groq=groq,
            ):
                data = json.dumps({"text": chunk})
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            logger.exception("Stream error")
            yield f"data: {json.dumps({'error': 'Generation failed'})}\n\n"
            return

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/clear")
@limiter.limit("10/minute")
async def clear_session(
    body: ClearRequest,
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    """Clear conversation history for a session."""
    # If no auth, require session_id to be a valid UUID
    if user is None and not _UUID_RE.match(body.session_id):
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    from app.core.thoth_chat import session_store

    session_store.clear(body.session_id)
    return JSONResponse(content={"status": "cleared"})
