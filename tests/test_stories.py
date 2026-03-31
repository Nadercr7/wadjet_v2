"""Stories API tests — listing, chapter access, interactions."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


async def test_stories_list(test_client: AsyncClient):
    resp = await test_client.get("/api/stories")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, (list, dict))


async def test_stories_invalid_id_format(test_client: AsyncClient):
    resp = await test_client.get("/api/stories/!!invalid!!")
    assert resp.status_code == 400


async def test_stories_nonexistent(test_client: AsyncClient):
    resp = await test_client.get("/api/stories/nonexistent-story-xyz")
    assert resp.status_code == 404


async def test_stories_chapter_invalid_story(test_client: AsyncClient):
    resp = await test_client.get("/api/stories/nonexistent-story/chapters/0")
    assert resp.status_code == 404


async def test_stories_valid_story():
    """If stories exist, loading one should work."""
    from app.core.stories_engine import load_all_stories

    stories = load_all_stories()
    if not stories:
        pytest.skip("No story files available")


async def test_stories_chapter_out_of_bounds(test_client: AsyncClient):
    """Accessing chapter beyond last → 404."""
    from app.core.stories_engine import load_all_stories

    stories = load_all_stories()
    if not stories:
        pytest.skip("No story files available")

    story_id = stories[0]["id"]
    resp = await test_client.get(f"/api/stories/{story_id}/chapters/9999")
    assert resp.status_code == 404


async def test_stories_get_story_success(test_client: AsyncClient):
    """GET /api/stories/{id} with a valid story returns full data."""
    from app.core.stories_engine import get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    resp = await test_client.get(f"/api/stories/{ids[0]}")
    assert resp.status_code == 200
    body = resp.json()
    assert "chapters" in body or "title" in body


async def test_stories_get_chapter_success(test_client: AsyncClient):
    """GET /api/stories/{id}/chapters/0 returns chapter data."""
    from app.core.stories_engine import get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    resp = await test_client.get(f"/api/stories/{ids[0]}/chapters/0")
    assert resp.status_code == 200
    body = resp.json()
    assert "chapter" in body
    assert "total_chapters" in body


async def test_stories_chapter_negative_index(test_client: AsyncClient):
    """Negative chapter index → 400."""
    from app.core.stories_engine import get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    resp = await test_client.get(f"/api/stories/{ids[0]}/chapters/-1")
    assert resp.status_code == 400


async def test_stories_interact_invalid_story(test_client: AsyncClient):
    """POST interact on nonexistent story → 404."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stories/nonexistent-story/interact",
        json={"chapter_index": 0, "interaction_index": 0, "answer": "a"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 404


async def test_stories_interact_invalid_id_format(test_client: AsyncClient):
    """POST interact with bad story ID → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stories/!!BAD!!/interact",
        json={"chapter_index": 0, "interaction_index": 0, "answer": "a"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


async def test_stories_list_has_count(test_client: AsyncClient):
    """List response includes count field."""
    resp = await test_client.get("/api/stories")
    body = resp.json()
    assert "count" in body
    assert body["count"] >= 0


async def test_stories_image_no_story(test_client: AsyncClient):
    """POST image generate for nonexistent story → 404."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stories/nonexistent-story/chapters/0/image",
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 404


async def test_stories_image_bad_story_id(test_client: AsyncClient):
    """POST image generate with bad story ID → 400."""
    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        "/api/stories/!!invalid!!/chapters/0/image",
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 400


# ── Interaction Scoring Tests (TEST-009) ──


async def test_interact_choose_glyph_correct(test_client: AsyncClient):
    """Submit correct answer to choose_glyph interaction → correct=True."""
    from app.core.stories_engine import get_chapter, get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    # Find a story with a choose_glyph interaction
    for story_id in ids:
        chapter = get_chapter(story_id, 0)
        if not chapter:
            continue
        interactions = chapter.get("interactions", [])
        for i, interaction in enumerate(interactions):
            if interaction["type"] == "choose_glyph":
                correct_answer = interaction["correct"]

                await test_client.get("/api/health")
                csrf = test_client.cookies.get("csrftoken", "")

                resp = await test_client.post(
                    f"/api/stories/{story_id}/interact",
                    json={
                        "chapter_index": 0,
                        "interaction_index": i,
                        "answer": correct_answer,
                    },
                    headers={"x-csrftoken": csrf},
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["correct"] is True
                assert body["type"] == "choose_glyph"
                return

    pytest.skip("No choose_glyph interaction found in any story chapter 0")


async def test_interact_choose_glyph_wrong(test_client: AsyncClient):
    """Submit wrong answer to choose_glyph interaction → correct=False."""
    from app.core.stories_engine import get_chapter, get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    for story_id in ids:
        chapter = get_chapter(story_id, 0)
        if not chapter:
            continue
        interactions = chapter.get("interactions", [])
        for i, interaction in enumerate(interactions):
            if interaction["type"] == "choose_glyph":
                correct = interaction["correct"]
                # Pick a wrong answer from options
                options = interaction.get("options", [])
                wrong = next(
                    (o["code"] for o in options if o["code"] != correct),
                    "WRONG",
                )

                await test_client.get("/api/health")
                csrf = test_client.cookies.get("csrftoken", "")

                resp = await test_client.post(
                    f"/api/stories/{story_id}/interact",
                    json={
                        "chapter_index": 0,
                        "interaction_index": i,
                        "answer": wrong,
                    },
                    headers={"x-csrftoken": csrf},
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["correct"] is False
                assert body["type"] == "choose_glyph"
                return

    pytest.skip("No choose_glyph interaction found")


async def test_interact_glyph_discovery(test_client: AsyncClient):
    """Glyph discovery interaction always returns correct=True."""
    from app.core.stories_engine import get_chapter, get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    for story_id in ids:
        chapter = get_chapter(story_id, 0)
        if not chapter:
            continue
        interactions = chapter.get("interactions", [])
        for i, interaction in enumerate(interactions):
            if interaction["type"] == "glyph_discovery":
                await test_client.get("/api/health")
                csrf = test_client.cookies.get("csrftoken", "")

                resp = await test_client.post(
                    f"/api/stories/{story_id}/interact",
                    json={
                        "chapter_index": 0,
                        "interaction_index": i,
                        "answer": "seen",
                    },
                    headers={"x-csrftoken": csrf},
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["correct"] is True
                assert body["type"] == "glyph_discovery"
                return

    pytest.skip("No glyph_discovery interaction found")


async def test_interact_out_of_bounds(test_client: AsyncClient):
    """Interaction index out of bounds → 404."""
    from app.core.stories_engine import get_story_ids

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    await test_client.get("/api/health")
    csrf = test_client.cookies.get("csrftoken", "")

    resp = await test_client.post(
        f"/api/stories/{ids[0]}/interact",
        json={"chapter_index": 0, "interaction_index": 999, "answer": "x"},
        headers={"x-csrftoken": csrf},
    )
    assert resp.status_code == 404


async def test_interact_write_word(test_client: AsyncClient):
    """Submit correct Gardiner code to write_word → correct=True."""
    from app.core.stories_engine import get_story_ids, load_story

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    for story_id in ids:
        story = load_story(story_id)
        if not story:
            continue
        for ch_idx, chapter in enumerate(story.get("chapters", [])):
            interactions = chapter.get("interactions", [])
            for i, interaction in enumerate(interactions):
                if interaction["type"] == "write_word":
                    target_code = interaction["gardiner_code"]

                    await test_client.get("/api/health")
                    csrf = test_client.cookies.get("csrftoken", "")

                    resp = await test_client.post(
                        f"/api/stories/{story_id}/interact",
                        json={
                            "chapter_index": ch_idx,
                            "interaction_index": i,
                            "answer": target_code,
                        },
                        headers={"x-csrftoken": csrf},
                    )
                    assert resp.status_code == 200
                    body = resp.json()
                    assert body["correct"] is True
                    assert body["type"] == "write_word"
                    assert body["gardiner_code"] == target_code
                    return

    pytest.skip("No write_word interaction found")


async def test_interact_story_decision(test_client: AsyncClient):
    """Submit a valid choice to story_decision → correct=True with outcome."""
    from app.core.stories_engine import get_story_ids, load_story

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    for story_id in ids:
        story = load_story(story_id)
        if not story:
            continue
        for ch_idx, chapter in enumerate(story.get("chapters", [])):
            interactions = chapter.get("interactions", [])
            for i, interaction in enumerate(interactions):
                if interaction["type"] == "story_decision":
                    choices = interaction.get("choices", [])
                    if not choices:
                        continue
                    choice_id = choices[0]["id"]

                    await test_client.get("/api/health")
                    csrf = test_client.cookies.get("csrftoken", "")

                    resp = await test_client.post(
                        f"/api/stories/{story_id}/interact",
                        json={
                            "chapter_index": ch_idx,
                            "interaction_index": i,
                            "answer": choice_id,
                        },
                        headers={"x-csrftoken": csrf},
                    )
                    assert resp.status_code == 200
                    body = resp.json()
                    assert body["correct"] is True
                    assert body["type"] == "story_decision"
                    assert body["choice_id"] == choice_id
                    assert "outcome" in body
                    return

    pytest.skip("No story_decision interaction found")


async def test_interact_story_decision_invalid_choice(test_client: AsyncClient):
    """Invalid choice in story_decision → 400."""
    from app.core.stories_engine import get_story_ids, load_story

    ids = get_story_ids()
    if not ids:
        pytest.skip("No story files available")

    for story_id in ids:
        story = load_story(story_id)
        if not story:
            continue
        for ch_idx, chapter in enumerate(story.get("chapters", [])):
            interactions = chapter.get("interactions", [])
            for i, interaction in enumerate(interactions):
                if interaction["type"] == "story_decision":
                    await test_client.get("/api/health")
                    csrf = test_client.cookies.get("csrftoken", "")

                    resp = await test_client.post(
                        f"/api/stories/{story_id}/interact",
                        json={
                            "chapter_index": ch_idx,
                            "interaction_index": i,
                            "answer": "nonexistent_choice_xyz",
                        },
                        headers={"x-csrftoken": csrf},
                    )
                    assert resp.status_code == 400
                    return

    pytest.skip("No story_decision interaction found")
