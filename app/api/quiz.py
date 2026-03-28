"""Quiz API — Egyptian heritage quiz endpoints.

GET  /api/quiz/question    — Get a random question (static pool)
POST /api/quiz/answer      — Check an answer
POST /api/quiz/generate    — Generate AI questions via Gemini
GET  /api/quiz/info        — Pool size and question types
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

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


class AnswerRequest(BaseModel):
    question_id: str = Field(..., min_length=1, max_length=100)
    answer: str = Field(..., min_length=1, max_length=500)


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
async def submit_answer(body: AnswerRequest):
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
                }
                for q in questions
            ],
            "count": len(questions),
        })
    except Exception:
        logger.exception("Quiz generation failed")
        raise HTTPException(status_code=500, detail="Failed to generate quiz")


@router.get("/info")
async def quiz_info():
    """Return quiz pool info."""
    return JSONResponse(content={
        "pool_size": get_pool_size(),
        "question_types": get_question_types(),
        "categories": QUIZ_CATEGORIES,
        "difficulties": VALID_DIFFICULTIES,
    })
