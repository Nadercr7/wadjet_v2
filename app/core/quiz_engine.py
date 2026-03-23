"""Quiz Engine — question bank & Gemini-generated quizzes.

Static pool from landmarks data (identify_monument, match_city, date_era)
plus AI-generated questions via Gemini for richer variety.
"""

from __future__ import annotations

import json
import logging
import random
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.core.landmarks import get_all

if TYPE_CHECKING:
    from app.core.gemini_service import GeminiService

logger = logging.getLogger(__name__)

QUESTION_TYPES = ["identify_monument", "match_city", "date_era"]
QUIZ_CATEGORIES = ["monuments", "pharaohs", "hieroglyphs", "mythology", "geography"]
VALID_DIFFICULTIES = ["easy", "medium", "hard"]


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    id: str
    question_type: str
    question: str
    options: list[str]
    correct_answer: str
    difficulty: str
    hint: str


@dataclass(frozen=True, slots=True)
class QuizResult:
    question_id: str
    is_correct: bool
    submitted_answer: str
    correct_answer: str
    explanation: str


@dataclass
class GeneratedQuizQuestion:
    id: str
    question: str
    options: list[str]
    correct_answer: str
    explanation: str
    category: str
    difficulty: str


# ── Static question pool ──

def _build_question_pool() -> list[QuizQuestion]:
    attractions = get_all()
    pool: list[QuizQuestion] = []
    n = 0

    for attr in attractions:
        if attr.description:
            n += 1
            wrong = [a.name for a in attractions if a.name != attr.name]
            random.seed(n)
            distractors = random.sample(wrong, min(3, len(wrong)))
            opts = [attr.name, *distractors]
            random.seed(n + 1000)
            random.shuffle(opts)
            pool.append(QuizQuestion(
                id=f"q-identify-{n}",
                question_type="identify_monument",
                question=f'Which Egyptian landmark is described as: "{attr.description}"?',
                options=opts,
                correct_answer=attr.name,
                difficulty="easy" if attr.popularity >= 8 else "medium",
                hint=f"It is located in {attr.city.value}.",
            ))

        if attr.city:
            n += 1
            all_cities = sorted({a.city.value for a in attractions})
            other = [c for c in all_cities if c != attr.city.value]
            random.seed(n)
            distractors = random.sample(other, min(3, len(other)))
            opts = [attr.city.value, *distractors]
            random.seed(n + 2000)
            random.shuffle(opts)
            pool.append(QuizQuestion(
                id=f"q-city-{n}",
                question_type="match_city",
                question=f"In which Egyptian city is {attr.name} located?",
                options=opts,
                correct_answer=attr.city.value,
                difficulty="easy" if attr.popularity >= 8 else "medium",
                hint=f"This is a {attr.type.value} site.",
            ))

        if attr.era:
            n += 1
            all_eras = sorted({a.era for a in attractions if a.era})
            other = [e for e in all_eras if e != attr.era]
            random.seed(n)
            distractors = random.sample(other, min(3, len(other)))
            opts = [attr.era, *distractors]
            random.seed(n + 3000)
            random.shuffle(opts)
            pool.append(QuizQuestion(
                id=f"q-era-{n}",
                question_type="date_era",
                question=f"Which historical era does {attr.name} belong to?",
                options=opts,
                correct_answer=attr.era,
                difficulty="medium" if attr.popularity >= 6 else "hard",
                hint=f"It is located in {attr.city.value}.",
            ))

    return pool


_QUESTION_POOL: list[QuizQuestion] = _build_question_pool()
_ID_INDEX: dict[str, QuizQuestion] = {q.id: q for q in _QUESTION_POOL}


# ── Public API ──

def get_random_question(
    question_type: str | None = None,
    difficulty: str | None = None,
) -> QuizQuestion | None:
    candidates = _QUESTION_POOL
    if question_type:
        candidates = [q for q in candidates if q.question_type == question_type]
    if difficulty:
        candidates = [q for q in candidates if q.difficulty == difficulty]
    return random.choice(candidates) if candidates else None


def check_answer(question_id: str, answer: str) -> QuizResult | None:
    q = _ID_INDEX.get(question_id)
    if q is None:
        return None
    correct = answer.strip().lower() == q.correct_answer.strip().lower()
    explanation = (
        f"Correct! {q.correct_answer} is the right answer."
        if correct
        else f"Incorrect. The correct answer is: {q.correct_answer}."
    )
    return QuizResult(
        question_id=question_id,
        is_correct=correct,
        submitted_answer=answer,
        correct_answer=q.correct_answer,
        explanation=explanation,
    )


def get_question_by_id(qid: str) -> QuizQuestion | None:
    return _ID_INDEX.get(qid)


def get_question_types() -> list[str]:
    return list(QUESTION_TYPES)


def get_pool_size() -> int:
    return len(_QUESTION_POOL)


# ── Gemini-generated questions ──

_QUIZ_SYSTEM_PROMPT = (
    "You are a quiz master specialising in ancient Egyptian heritage. "
    "Generate multiple-choice quiz questions that are educational, "
    "accurate, and engaging. Each question must have exactly 4 options "
    "with exactly 1 correct answer. Never make up historical facts."
)

_QUIZ_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "correct_answer": {"type": "string"},
                    "explanation": {"type": "string"},
                    "category": {"type": "string"},
                    "difficulty": {"type": "string"},
                },
                "required": ["question", "options", "correct_answer", "explanation"],
            },
        }
    },
    "required": ["questions"],
}


async def generate_quiz(
    gemini: GeminiService,
    *,
    difficulty: str = "medium",
    category: str = "monuments",
    count: int = 5,
) -> list[GeneratedQuizQuestion]:
    count = max(1, min(count, 10))
    prompt = (
        f"Generate exactly {count} multiple-choice quiz question(s) about "
        f"Egyptian heritage.\n\n"
        f"Requirements:\n"
        f"- Category: {category}\n"
        f"- Difficulty: {difficulty}\n"
        f"- Language: English\n"
        f"- Each question must have exactly 4 options\n"
        f"- Exactly 1 option must be the correct answer\n"
        f"- The correct_answer field must exactly match one of the options\n"
        f"- Include a brief explanation of why the answer is correct\n"
        f"- Questions must be factually accurate\n\n"
        f"Difficulty guide:\n"
        f"- easy: well-known facts most tourists would know\n"
        f"- medium: requires some knowledge of Egyptian history\n"
        f"- hard: specialist knowledge, lesser-known facts\n\n"
        f"Return a JSON object with a 'questions' array."
    )

    raw = await gemini.generate_json(
        prompt,
        system_instruction=_QUIZ_SYSTEM_PROMPT,
        temperature=0.9,
        max_output_tokens=4096,
        response_schema=_QUIZ_JSON_SCHEMA,
    )

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.error("Quiz JSON parse error: %s", raw[:200])
        return []

    results: list[GeneratedQuizQuestion] = []
    for rq in data.get("questions", []):
        text = rq.get("question", "")
        options = rq.get("options", [])
        correct = rq.get("correct_answer", "")
        if not text or len(options) != 4 or correct not in options:
            continue
        results.append(GeneratedQuizQuestion(
            id=f"ai-{uuid.uuid4().hex[:12]}",
            question=text,
            options=options,
            correct_answer=correct,
            explanation=rq.get("explanation", ""),
            category=rq.get("category", category),
            difficulty=rq.get("difficulty", difficulty),
        ))

    logger.info("Quiz generated: %d/%d questions", len(results), count)
    return results
