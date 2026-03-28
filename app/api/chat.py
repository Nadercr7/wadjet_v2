"""Chat API — Thoth AI chatbot endpoints.

POST /api/chat          — Send message, get JSON reply
GET  /api/chat/stream   — SSE streaming response
POST /api/chat/clear    — Clear conversation session
"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
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


@router.get("/stream")
async def chat_stream(
    message: str,
    session_id: str,
    request: Request,
    landmark: str | None = None,
):
    """SSE streaming chat — sends text chunks as Server-Sent Events."""
    from app.core.thoth_chat import chat_stream as _chat_stream

    if not message or len(message) > 2000:
        raise HTTPException(status_code=400, detail="Invalid message")
    if not session_id or len(session_id) > 128:
        raise HTTPException(status_code=400, detail="Invalid session_id")
    if landmark and len(landmark) > 200:
        raise HTTPException(status_code=400, detail="Invalid landmark")

    gemini = _get_gemini(request)
    grok = _get_grok(request)
    groq = _get_groq(request)

    async def event_generator():
        try:
            async for chunk in _chat_stream(
                gemini,
                message,
                session_id=session_id,
                landmark=landmark,
                grok=grok,
                groq=groq,
            ):
                data = json.dumps({"text": chunk})
                yield f"data: {data}\n\n"
            yield "data: [DONE]\n\n"
        except Exception:
            logger.exception("Stream error")
            yield f"data: {json.dumps({'error': 'Generation failed'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/clear")
async def clear_session(body: ClearRequest):
    """Clear conversation history for a session."""
    from app.core.thoth_chat import session_store

    session_store.clear(body.session_id)
    return JSONResponse(content={"status": "cleared"})
