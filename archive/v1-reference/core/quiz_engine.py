"""
Wadjet AI - Quiz question bank & scoring engine.

Provides a static pool of quiz questions derived from the attractions
data **plus** Gemini-generated questions (Phase 3.11).

Static question types:

* **identify_monument** - "Which monument is described as ...?"
* **match_city** - "In which city is ... located?"
* **date_era** - "Which historical era does ... belong to?"

Gemini-generated question categories:
  monuments, pharaohs, hieroglyphs, mythology, geography

Public helpers
--------------
``get_random_question(question_type=None)``
    Return a random ``QuizQuestion``.  Optionally filter by type.
``check_answer(question_id, answer)``
    Grade a submitted answer and return a ``QuizResult``.
``get_question_types()``
    Return the list of supported question type strings.
``get_question_by_id(qid)``
    O(1) lookup by question ID.
``generate_quiz(gemini_service, difficulty, category, language, count)``
    Generate AI-powered quiz questions via Gemini (Phase 3.11).
"""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING

import structlog

from app.core.attractions_data import get_all as get_all_attractions

if TYPE_CHECKING:
    from app.core.gemini_service import GeminiService

logger = structlog.get_logger("wadjet.quiz")

# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

QUESTION_TYPES: list[str] = ["identify_monument", "match_city", "date_era"]

# Categories for Gemini-generated questions (Phase 3.11)
QUIZ_CATEGORIES: list[str] = [
    "monuments",
    "pharaohs",
    "hieroglyphs",
    "mythology",
    "geography",
]

VALID_DIFFICULTIES: list[str] = ["easy", "medium", "hard"]


@dataclass(frozen=True, slots=True)
class QuizQuestion:
    """A single quiz question with answer options."""

    id: str
    question_type: str
    question: str
    options: list[str]
    correct_answer: str
    difficulty: str  # easy | medium | hard
    hint: str


@dataclass(frozen=True, slots=True)
class QuizResult:
    """Result of grading a quiz answer."""

    question_id: str
    is_correct: bool
    submitted_answer: str
    correct_answer: str
    explanation: str


# ---------------------------------------------------------------------------
# Question generation from attractions data
# ---------------------------------------------------------------------------


def _build_question_pool() -> list[QuizQuestion]:
    """Build the full question pool from attractions data.

    Called once at import time.  Generates deterministic questions so
    IDs are stable between restarts.
    """
    attractions = get_all_attractions()
    pool: list[QuizQuestion] = []
    q_counter = 0

    for attr in attractions:
        # ----- Type 1: identify_monument ------------------------------------
        # "Which landmark has this description?"
        if attr.description:
            q_counter += 1
            wrong = [a.name for a in attractions if a.name != attr.name]
            random.seed(q_counter)
            distractors = random.sample(wrong, min(3, len(wrong)))
            opts = [attr.name, *distractors]
            random.seed(q_counter + 1000)
            random.shuffle(opts)
            pool.append(
                QuizQuestion(
                    id=f"q-identify-{q_counter}",
                    question_type="identify_monument",
                    question=f'Which Egyptian landmark is described as: "{attr.description}"?',
                    options=opts,
                    correct_answer=attr.name,
                    difficulty="easy" if attr.popularity >= 8 else "medium",
                    hint=f"It is located in {attr.city.value}.",
                ),
            )

        # ----- Type 2: match_city -------------------------------------------
        # "In which city is X located?"
        if attr.city:
            q_counter += 1
            all_cities = sorted({a.city.value for a in attractions})
            other_cities = [c for c in all_cities if c != attr.city.value]
            random.seed(q_counter)
            distractors = random.sample(other_cities, min(3, len(other_cities)))
            opts = [attr.city.value, *distractors]
            random.seed(q_counter + 2000)
            random.shuffle(opts)
            pool.append(
                QuizQuestion(
                    id=f"q-city-{q_counter}",
                    question_type="match_city",
                    question=f"In which Egyptian city is {attr.name} located?",
                    options=opts,
                    correct_answer=attr.city.value,
                    difficulty="easy" if attr.popularity >= 8 else "medium",
                    hint=f"This is a {attr.type.value} site.",
                ),
            )

        # ----- Type 3: date_era --------------------------------------------
        # "Which historical era does X belong to?"
        if attr.era:
            q_counter += 1
            all_eras = sorted({a.era for a in attractions if a.era})
            other_eras = [e for e in all_eras if e != attr.era]
            random.seed(q_counter)
            distractors = random.sample(other_eras, min(3, len(other_eras)))
            opts = [attr.era, *distractors]
            random.seed(q_counter + 3000)
            random.shuffle(opts)
            pool.append(
                QuizQuestion(
                    id=f"q-era-{q_counter}",
                    question_type="date_era",
                    question=f"Which historical era does {attr.name} belong to?",
                    options=opts,
                    correct_answer=attr.era,
                    difficulty="medium" if attr.popularity >= 6 else "hard",
                    hint=f"It is located in {attr.city.value}.",
                ),
            )

    return pool


# ---------------------------------------------------------------------------
# Module-level data  (built once)
# ---------------------------------------------------------------------------

_QUESTION_POOL: list[QuizQuestion] = _build_question_pool()
_ID_INDEX: dict[str, QuizQuestion] = {q.id: q for q in _QUESTION_POOL}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_random_question(
    question_type: str | None = None,
    difficulty: str | None = None,
) -> QuizQuestion | None:
    """Return a random question, optionally filtered by type and/or difficulty.

    Returns ``None`` when the pool (after filtering) is empty.
    """
    candidates = _QUESTION_POOL
    if question_type:
        candidates = [q for q in candidates if q.question_type == question_type]
    if difficulty:
        candidates = [q for q in candidates if q.difficulty == difficulty]
    if not candidates:
        return None
    return random.choice(candidates)


def check_answer(question_id: str, answer: str) -> QuizResult | None:
    """Grade a submitted answer.

    Returns ``None`` when *question_id* is unknown.
    The comparison is case-insensitive and strips whitespace.
    """
    q = _ID_INDEX.get(question_id)
    if q is None:
        return None
    is_correct = answer.strip().lower() == q.correct_answer.strip().lower()
    explanation = (
        f"Correct! {q.correct_answer} is the right answer."
        if is_correct
        else f"Incorrect. The correct answer is: {q.correct_answer}."
    )
    return QuizResult(
        question_id=question_id,
        is_correct=is_correct,
        submitted_answer=answer,
        correct_answer=q.correct_answer,
        explanation=explanation,
    )


def get_question_by_id(question_id: str) -> QuizQuestion | None:
    """O(1) lookup by question ID.  Returns ``None`` if not found."""
    return _ID_INDEX.get(question_id)


def get_question_types() -> list[str]:
    """Return the sorted list of supported question type strings."""
    return list(QUESTION_TYPES)


def get_pool_size() -> int:
    """Return the total number of questions in the pool."""
    return len(_QUESTION_POOL)


# ---------------------------------------------------------------------------
# Gemini-generated quiz questions (Phase 3.11)
# ---------------------------------------------------------------------------

# Language-specific quiz system prompts
_QUIZ_SYSTEM_PROMPTS: dict[str, str] = {
    "en": (
        "You are a quiz master specialising in ancient Egyptian heritage. "
        "Generate multiple-choice quiz questions that are educational, "
        "accurate, and engaging. Each question must have exactly 4 options "
        "with exactly 1 correct answer. Never make up historical facts."
    ),
    "ar": (
        "أنت خبير اختبارات متخصص في التراث المصري القديم. "
        "أنشئ أسئلة اختيار من متعدد تعليمية ودقيقة وجذابة. "
        "يجب أن يحتوي كل سؤال على 4 خيارات بالضبط مع إجابة صحيحة واحدة. "
        "لا تختلق حقائق تاريخية أبداً."
    ),
    "fr": (
        "Vous etes un maitre de quiz specialise dans le patrimoine egyptien ancien. "
        "Generez des questions a choix multiples educatives, precises et captivantes. "
        "Chaque question doit avoir exactement 4 options avec exactement 1 bonne reponse. "
        "N'inventez jamais de faits historiques."
    ),
    "de": (
        "Sie sind ein Quiz-Meister, der sich auf das altaegyptische Erbe spezialisiert hat. "
        "Erstellen Sie Multiple-Choice-Quizfragen, die lehrreich, genau und fesselnd sind. "
        "Jede Frage muss genau 4 Optionen mit genau 1 richtigen Antwort haben. "
        "Erfinden Sie niemals historische Fakten."
    ),
}

_QUIZ_JSON_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "correct_answer": {"type": "string"},
                    "explanation": {"type": "string"},
                    "category": {"type": "string"},
                    "difficulty": {"type": "string"},
                },
                "required": [
                    "question",
                    "options",
                    "correct_answer",
                    "explanation",
                    "category",
                    "difficulty",
                ],
            },
        }
    },
    "required": ["questions"],
}


def _build_quiz_prompt(
    difficulty: str,
    category: str,
    language: str,
    count: int,
) -> str:
    """Build the Gemini prompt for quiz generation."""
    lang_label = {
        "en": "English",
        "ar": "Arabic",
        "fr": "French",
        "de": "German",
    }.get(language, "English")

    return (
        f"Generate exactly {count} multiple-choice quiz question(s) about "
        f"Egyptian heritage.\n\n"
        f"Requirements:\n"
        f"- Category: {category}\n"
        f"- Difficulty: {difficulty}\n"
        f"- Language: {lang_label} (all text must be in {lang_label})\n"
        f"- Each question must have exactly 4 options\n"
        f"- Exactly 1 option must be the correct answer\n"
        f"- The correct_answer field must exactly match one of the options\n"
        f"- Include a brief explanation of why the answer is correct\n"
        f"- Questions must be factually accurate\n"
        f"- Make questions diverse (don't repeat similar topics)\n\n"
        f"Difficulty guide:\n"
        f"- easy: well-known facts most tourists would know\n"
        f"- medium: requires some knowledge of Egyptian history\n"
        f"- hard: specialist knowledge, lesser-known facts\n\n"
        f"Return a JSON object with a 'questions' array."
    )


@dataclass
class GeneratedQuizQuestion:
    """A single Gemini-generated quiz question (Phase 3.11)."""

    id: str
    question: str
    options: list[str]
    correct_answer: str
    explanation: str
    category: str
    difficulty: str
    language: str


async def generate_quiz(
    gemini_service: GeminiService,
    *,
    difficulty: str = "medium",
    category: str = "monuments",
    language: str = "en",
    count: int = 5,
) -> list[GeneratedQuizQuestion]:
    """Generate AI-powered quiz questions via Gemini.

    Parameters
    ----------
    gemini_service:
        Injected Gemini service instance.
    difficulty:
        One of ``easy``, ``medium``, ``hard``.
    category:
        One of ``monuments``, ``pharaohs``, ``hieroglyphs``,
        ``mythology``, ``geography``.
    language:
        ISO 639-1 code (en/ar/fr/de).
    count:
        Number of questions to generate (1-10).

    Returns
    -------
    list[GeneratedQuizQuestion]
        List of validated quiz questions.
    """
    count = max(1, min(count, 10))

    system_prompt = _QUIZ_SYSTEM_PROMPTS.get(language, _QUIZ_SYSTEM_PROMPTS["en"])
    prompt = _build_quiz_prompt(difficulty, category, language, count)

    logger.info(
        "quiz_generate_request",
        difficulty=difficulty,
        category=category,
        language=language,
        count=count,
    )

    raw_json = await gemini_service.generate_json(
        prompt,
        system_instruction=system_prompt,
        temperature=0.9,  # creative but grounded
        max_output_tokens=4096,
        response_schema=_QUIZ_JSON_SCHEMA,
    )

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.error("quiz_generate_json_parse_error", raw=raw_json[:200])
        return []

    raw_questions = data.get("questions", [])
    results: list[GeneratedQuizQuestion] = []

    for raw_q in raw_questions:
        # Validate structure
        question_text = raw_q.get("question", "")
        options = raw_q.get("options", [])
        correct = raw_q.get("correct_answer", "")
        explanation = raw_q.get("explanation", "")
        cat = raw_q.get("category", category)
        diff = raw_q.get("difficulty", difficulty)

        if not question_text or len(options) != 4 or not correct:
            logger.warning(
                "quiz_generate_skip_invalid",
                question=question_text[:60],
                options_count=len(options),
            )
            continue

        # Ensure correct_answer is in options
        if correct not in options:
            logger.warning(
                "quiz_generate_correct_not_in_options",
                correct=correct,
                options=options,
            )
            continue

        results.append(
            GeneratedQuizQuestion(
                id=f"ai-{uuid.uuid4().hex[:12]}",
                question=question_text,
                options=options,
                correct_answer=correct,
                explanation=explanation,
                category=cat,
                difficulty=diff,
                language=language,
            )
        )

    logger.info(
        "quiz_generate_complete",
        requested=count,
        generated=len(results),
        category=category,
        difficulty=difficulty,
        language=language,
    )

    return results
