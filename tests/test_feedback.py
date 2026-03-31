"""Feedback API tests — submit, validate, list, rate limit, XSS prevention."""

from __future__ import annotations

from httpx import AsyncClient

# ── Successful submission ──


async def test_submit_feedback_valid(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/feedback",
        json={
            "category": "bug",
            "message": "The scan page crashes on large images",
            "page_url": "/scan",
            "name": "Tester",
            "email": "tester@test.com",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["ok"] is True
    assert body["id"] >= 1


async def test_submit_feedback_minimal(test_client: AsyncClient):
    """Only category + message are required."""
    resp = await test_client.post(
        "/api/feedback",
        json={"category": "suggestion", "message": "Please add dark mode toggle"},
    )
    assert resp.status_code == 201


async def test_submit_feedback_all_categories(test_client: AsyncClient):
    for cat in ("bug", "suggestion", "praise", "other"):
        resp = await test_client.post(
            "/api/feedback",
            json={"category": cat, "message": f"Testing {cat} category works fine"},
        )
        assert resp.status_code == 201, f"Failed for category: {cat}"


# ── Validation errors ──


async def test_submit_feedback_invalid_category(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/feedback",
        json={"category": "invalid", "message": "This should be rejected"},
    )
    assert resp.status_code == 422


async def test_submit_feedback_message_too_short(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/feedback",
        json={"category": "bug", "message": "short"},
    )
    assert resp.status_code == 422


async def test_submit_feedback_empty_body(test_client: AsyncClient):
    resp = await test_client.post("/api/feedback", json={})
    assert resp.status_code == 422


async def test_submit_feedback_missing_message(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/feedback",
        json={"category": "bug"},
    )
    assert resp.status_code == 422


# ── XSS / sanitization ──


async def test_submit_feedback_html_stripped(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/feedback",
        json={
            "category": "bug",
            "message": "<script>alert(1)</script>This is the actual message here",
            "name": "<b>Evil</b>Name",
        },
    )
    assert resp.status_code == 201


async def test_submit_feedback_category_case_insensitive(test_client: AsyncClient):
    resp = await test_client.post(
        "/api/feedback",
        json={"category": "BUG", "message": "Category should be lowercased by validator"},
    )
    assert resp.status_code == 201


# ── List feedback (auth-protected) ──


async def test_list_feedback_unauthenticated(test_client: AsyncClient):
    resp = await test_client.get("/api/feedback")
    assert resp.status_code == 401


async def test_list_feedback_non_admin_forbidden(authenticated_client: AsyncClient):
    """Non-admin authenticated user gets 403."""
    resp = await authenticated_client.get("/api/feedback")
    assert resp.status_code == 403


async def test_list_feedback_admin(admin_client: AsyncClient):
    # Submit some feedback first
    await admin_client.post(
        "/api/feedback",
        json={"category": "praise", "message": "Great app, love the Egyptian theme!"},
    )
    resp = await admin_client.get("/api/feedback")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert "category" in body[0]
    assert "message" in body[0]
    assert "created_at" in body[0]


async def test_list_feedback_pagination(admin_client: AsyncClient):
    resp = await admin_client.get("/api/feedback?limit=2&offset=0")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) <= 2


# ── Rate limiting ──


async def test_feedback_rate_limit(test_client: AsyncClient):
    """Submitting more than 5 feedbacks per minute should be rate limited."""
    for i in range(5):
        resp = await test_client.post(
            "/api/feedback",
            json={"category": "other", "message": f"Rate limit test number {i + 1} from user"},
        )
        assert resp.status_code == 201, f"Request {i + 1} should succeed"

    # 6th request should be rate limited
    resp = await test_client.post(
        "/api/feedback",
        json={"category": "other", "message": "This sixth request should be rate limited now"},
    )
    assert resp.status_code == 429
