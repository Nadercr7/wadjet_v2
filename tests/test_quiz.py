"""Quiz API tests — random question, answer checking, info, HMAC verification."""

from __future__ import annotations

from httpx import AsyncClient


async def test_quiz_info(test_client: AsyncClient):
    """GET /api/quiz/info returns pool size and metadata."""
    resp = await test_client.get("/api/quiz/info")
    assert resp.status_code == 200
    body = resp.json()
    assert "pool_size" in body
    assert "categories" in body
    assert "difficulties" in body


async def test_quiz_random_question(test_client: AsyncClient):
    """GET /api/quiz/question returns a question."""
    resp = await test_client.get("/api/quiz/question")
    if resp.status_code == 404:
        # No questions in pool — that's fine for test env
        return
    assert resp.status_code == 200
    body = resp.json()
    assert "question" in body
    assert "options" in body


async def test_quiz_answer_not_found(test_client: AsyncClient):
    """POST /api/quiz/answer with nonexistent question → 404."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/quiz/answer",
        json={"question_id": "nonexistent-id-xyz", "answer": "A"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 404


async def test_quiz_generate_no_gemini(test_client: AsyncClient):
    """POST /api/quiz/generate without Gemini → 503."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/quiz/generate",
        json={"difficulty": "medium", "category": "monuments", "count": 1},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 503


async def test_quiz_check_ai_wrong_signature(test_client: AsyncClient):
    """POST /api/quiz/check-ai with wrong HMAC → is_correct=False."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/quiz/check-ai",
        json={"answer": "Cairo", "signature": "a" * 64},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["is_correct"] is False


async def test_quiz_answer_valid_question(test_client: AsyncClient):
    """POST /api/quiz/answer with a real question → returns result."""
    # First get a question
    resp = await test_client.get("/api/quiz/question")
    if resp.status_code == 404:
        return  # no questions available
    q = resp.json()

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    # Submit a wrong answer (just to exercise the code path)
    resp = await test_client.post(
        "/api/quiz/answer",
        json={"question_id": q["id"], "answer": "definitely_wrong_answer"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "is_correct" in body
    assert body["question_id"] == q["id"]


async def test_quiz_question_with_invalid_filter(test_client: AsyncClient):
    """GET /api/quiz/question with impossible filter → 404."""
    resp = await test_client.get("/api/quiz/question?question_type=nonexistent_type_xyz")
    assert resp.status_code == 404


async def test_quiz_generate_invalid_difficulty(test_client: AsyncClient):
    """POST /api/quiz/generate with invalid difficulty → 400."""
    from unittest.mock import MagicMock

    test_client._transport.app.state.gemini = MagicMock()  # type: ignore[attr-defined]
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/quiz/generate",
        json={"difficulty": "impossible", "category": "monuments", "count": 1},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_quiz_generate_invalid_category(test_client: AsyncClient):
    """POST /api/quiz/generate with invalid category → 400."""
    from unittest.mock import MagicMock

    test_client._transport.app.state.gemini = MagicMock()  # type: ignore[attr-defined]
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/quiz/generate",
        json={"difficulty": "medium", "category": "nonexistent_cat", "count": 1},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400
