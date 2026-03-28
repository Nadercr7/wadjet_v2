"""Quiz API — Egyptian heritage quiz endpoints.

GET  /api/quiz/question    — Get a random question (static pool)
POST /api/quiz/answer      — Check an answer
POST /api/quiz/generate    — Generate AI questions via Gemini
POST /api/quiz/check-ai    — Check AI-generated question answer (HMAC-verified)
GET  /api/quiz/info        — Pool size and question types
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.rate_limit import limiter

from app.core.quiz_engine import (
    QUIZ_CATEGORIES,
    VALID_DIFFICULTIES,
    check_answer,
    generate_quiz,
    get_pool_size,
    get_question_types,
    get_random_question,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/quiz", tags=["quiz"])

# Derive HMAC secret from CSRF secret for stability across workers/restarts.
# Falls back to random bytes if no CSRF secret is configured.
from app.config import settings as _quiz_settings
_QUIZ_SECRET = (
    hashlib.sha256((_quiz_settings.csrf_secret or "").encode()).digest()
    if _quiz_settings.csrf_secret
    else os.urandom(32)
)


def _sign_answer(answer: str) -> str:
    """HMAC-sign a correct answer so clients can't tamper."""
    return hmac.new(_QUIZ_SECRET, answer.encode("utf-8"), hashlib.sha256).hexdigest()


def _verify_answer(answer: str, signature: str) -> bool:
    """Verify an answer matches its HMAC signature."""
    expected = hmac.new(_QUIZ_SECRET, answer.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


class AnswerRequest(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=100)
    answer: str = Field(..., min_length=1, max_length=500)


class AiAnswerRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=500)
    signature: str = Field(..., min_length=64, max_length=64)


class GenerateRequest(BaseModel):
    difficulty: str = Field(default="medium")
    category: str = Field(default="monuments")
    count: int = Field(default=5, ge=1, le=10)


def _question_to_dict(q) -> dict:
    return {
        "id": q.id,
        "question": q.question,
        "options": q.options,
        "difficulty": getattr(q, "difficulty", "medium"),
        "hint": getattr(q, "hint", ""),
        "question_type": getattr(q, "question_type", ""),
    }


@router.get("/question")
async def random_question(
    question_type: str | None = None,
    difficulty: str | None = None,
):
    """Get a random quiz question from the static pool."""
    q = get_random_question(question_type=question_type, difficulty=difficulty)
    if q is None:
        raise HTTPException(status_code=404, detail="No questions match the filters")
    return JSONResponse(content=_question_to_dict(q))


@router.post("/answer")
@limiter.limit("30/minute")
async def submit_answer(body: AnswerRequest, request: Request):
    """Check an answer and return result."""
    result = check_answer(body.question_id, body.answer)
    if result is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return JSONResponse(content={
        "question_id": result.question_id,
        "is_correct": result.is_correct,
        "submitted_answer": result.submitted_answer,
        "correct_answer": result.correct_answer,
        "explanation": result.explanation,
    })


@router.post("/generate")
@limiter.limit("10/minute")
async def generate_quiz_endpoint(body: GenerateRequest, request: Request):
    """Generate AI-powered quiz questions via Gemini."""
    gemini = getattr(request.app.state, "gemini", None)
    if gemini is None:
        raise HTTPException(status_code=503, detail="AI service not available")

    if body.difficulty not in VALID_DIFFICULTIES:
        raise HTTPException(status_code=400, detail=f"Invalid difficulty. Use: {VALID_DIFFICULTIES}")
    if body.category not in QUIZ_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Use: {QUIZ_CATEGORIES}")

    try:
        questions = await generate_quiz(
            gemini,
            difficulty=body.difficulty,
            category=body.category,
            count=body.count,
        )
        return JSONResponse(content={
            "questions": [
                {
                    "id": q.id,
                    "question": q.question,
                    "options": q.options,
                    "difficulty": q.difficulty,
                    "category": q.category,
                    "answer_sig": _sign_answer(q.correct_answer),
                }
                for q in questions
            ],
            "count": len(questions),
        })
    except Exception:
        logger.exception("Quiz generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate quiz")


@router.post("/check-ai")
@limiter.limit("30/minute")
async def check_ai_answer(body: AiAnswerRequest, request: Request):
    """Check an AI-generated quiz answer using HMAC verification.

    The client sends the selected answer + the signature it received
    when the question was generated. No correct answer is ever exposed.
    """
    is_correct = _verify_answer(body.answer, body.signature)
    return JSONResponse(content={
        "is_correct": is_correct,
        "submitted_answer": body.answer,
        "explanation": (
            "Correct! Well done."
            if is_correct
            else "Incorrect."
        ),
    })


@router.get("/info")
async def quiz_info():
    """Return quiz pool info."""
    return JSONResponse(content={
        "pool_size": get_pool_size(),
        "question_types": get_question_types(),
        "categories": QUIZ_CATEGORIES,
        "difficulties": VALID_DIFFICULTIES,
    })
