"""Core logic tests — stories, gardiner, auth helpers."""

from __future__ import annotations

# ── Stories Engine ──


def test_load_all_stories():
    from app.core.stories_engine import load_all_stories

    stories = load_all_stories()
    # Should return a list (may be empty if no story files exist)
    assert isinstance(stories, list)


def test_load_story_valid():
    from app.core.stories_engine import load_all_stories, load_story

    stories = load_all_stories()
    if stories:
        story = load_story(stories[0]["id"])
        assert story is not None
        assert "id" in story
        assert "title" in story
        assert "chapters" in story


def test_load_story_not_found():
    from app.core.stories_engine import load_story

    result = load_story("nonexistent-story-xyz")
    assert result is None


def test_load_story_invalid_id():
    from app.core.stories_engine import load_story

    result = load_story("../../etc/passwd")
    assert result is None


def test_get_story_ids():
    from app.core.stories_engine import get_story_ids

    ids = get_story_ids()
    assert isinstance(ids, list)


def test_get_chapter_out_of_bounds():
    from app.core.stories_engine import get_chapter, get_story_ids

    ids = get_story_ids()
    if ids:
        result = get_chapter(ids[0], 9999)
        assert result is None


# ── Gardiner Lookup ──


def test_gardiner_lookup_a1():
    from app.core.gardiner import GARDINER_TRANSLITERATION

    assert "A1" in GARDINER_TRANSLITERATION
    sign = GARDINER_TRANSLITERATION["A1"]
    assert sign.code == "A1"
    assert sign.description


def test_gardiner_has_many_signs():
    from app.core.gardiner import GARDINER_TRANSLITERATION

    assert len(GARDINER_TRANSLITERATION) > 100


def test_gardiner_sign_types():
    from app.core.gardiner import GARDINER_TRANSLITERATION, SignType

    types_found = set()
    for sign in GARDINER_TRANSLITERATION.values():
        types_found.add(sign.sign_type)
    # Should have at least uniliterals and biliterals
    assert SignType.UNILITERAL in types_found


# ── Auth Helpers ──


def test_hash_and_verify_password():
    from app.auth.password import hash_password, verify_password

    hashed = hash_password("MySecret123")
    assert hashed != "MySecret123"
    assert verify_password("MySecret123", hashed)
    assert not verify_password("WrongPass", hashed)


def test_create_and_decode_access_token():
    from app.auth.jwt import create_access_token, decode_token

    token = create_access_token("user-123")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-123"


def test_create_refresh_token():
    from app.auth.jwt import create_refresh_token, decode_token

    token, expires = create_refresh_token("user-456")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_decode_invalid_token():
    from app.auth.jwt import decode_token

    result = decode_token("not.a.valid.token")
    assert result is None


def test_decode_expired_token():
    from datetime import datetime, timedelta

    from jose import jwt as jose_jwt

    token = jose_jwt.encode(
        {"sub": "user", "exp": datetime.utcnow() - timedelta(hours=1)},
        "test-jwt-secret-do-not-use-in-production",
        algorithm="HS256",
    )
    from app.auth.jwt import decode_token

    result = decode_token(token)
    assert result is None
