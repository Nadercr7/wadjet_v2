"""Translation API endpoint — accepts JSON transliteration input.

POST /api/translate — Translate MdC transliteration to English + Arabic
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["translate"])


class TranslateRequest(BaseModel):
    transliteration: str
    gardiner_sequence: str = ""


@router.post("/translate")
async def translate_transliteration(req: TranslateRequest, request: Request):
    """Translate MdC transliteration to English and Arabic.

    Uses the RAGTranslator from app.state (async, cached, Gemini→Groq→Grok).
    """
    if not req.transliteration or not req.transliteration.strip():
        raise HTTPException(status_code=400, detail="Empty transliteration")

    translator = getattr(request.app.state, "translator", None)

    if translator is None:
        return JSONResponse(content={
            "transliteration": req.transliteration,
            "english": "",
            "arabic": "",
            "error": "Translation service unavailable",
        })

    try:
        result = await translator.translate_async(
            req.transliteration,
            gardiner_sequence=req.gardiner_sequence,
        )
        return JSONResponse(content={
            "transliteration": req.transliteration,
            "english": result.get("english", ""),
            "arabic": result.get("arabic", ""),
            "context": result.get("context", ""),
            "error": result.get("error") or "",
            "provider": result.get("provider", ""),
            "latency_ms": result.get("latency_ms", 0),
            "from_cache": result.get("from_cache", False),
        })
    except Exception as e:
        logger.exception("Translation failed")
        raise HTTPException(status_code=500, detail=f"Translation error: {e}") from e
