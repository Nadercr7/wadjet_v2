# TESTING PLAN — All Phases

> Test strategy: existing pytest suite + new test cases per phase.

---

## Current Test Suite

```
tests/
├── conftest.py          # Fixtures: app client, test DB, auth helpers
├── test_auth.py         # Auth endpoints
├── test_routes.py       # HTML page routes
├── test_scan.py         # Scan pipeline
├── test_translate.py    # Translation API
├── test_dictionary.py   # Dictionary API
├── test_write.py        # Write API
├── test_explore.py      # Explore API
├── test_chat.py         # Thoth chat
├── test_stories.py      # Stories API
├── test_audio.py        # TTS/STT
├── test_quiz.py         # Legacy quiz
├── test_user.py         # User profile
├── test_db.py           # Database operations
├── test_core.py         # Core business logic
├── test_feedback.py     # Feedback endpoints
├── test_security.py     # Security-specific tests
├── test_smoke.py        # Smoke tests (all routes 200)
```

### Running Tests

```bash
# Activate venv
.venv\Scripts\activate

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_auth.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

---

## Phase 0: Credentials Verification Tests

| # | Test | File | Type |
|---|------|------|------|
| 0.1 | Server starts with all env vars set | `test_smoke.py` | Smoke |
| 0.2 | Config loads all settings | `test_core.py` | Unit |
| 0.3 | `.env.example` has all keys | Manual | Checklist |

---

## Phase 1: Security Audit Tests

| # | Test | File | Expected |
|---|------|------|----------|
| 1.1 | CSP header present on all responses | `test_security.py` | Header exists |
| 1.2 | X-Frame-Options header present | `test_security.py` | DENY |
| 1.3 | X-Content-Type-Options present | `test_security.py` | nosniff |
| 1.4 | Upload non-image file rejected | `test_scan.py` | 400 |
| 1.5 | Upload oversized file rejected | `test_scan.py` | 413 |
| 1.6 | Register with weak password rejected | `test_auth.py` | 422 |
| 1.7 | Rate limit on login (11th request blocked) | `test_auth.py` | 429 |
| 1.8 | Error response hides stack trace | `test_security.py` | No traceback |
| 1.9 | Login with non-existent email (constant time) | `test_auth.py` | 401, ~same timing |
| 1.10 | CSRF token validated on POST | `test_security.py` | 403 without token |

### Security Test Template

```python
# tests/test_security.py additions

async def test_csp_header(client):
    response = await client.get("/")
    assert "content-security-policy" in response.headers

async def test_x_frame_options(client):
    response = await client.get("/")
    assert response.headers.get("x-frame-options") == "DENY"

async def test_upload_non_image_rejected(client):
    fake_exe = b"MZ\x90\x00" + b"\x00" * 100  # PE header
    response = await client.post("/api/scan", files={"file": ("test.jpg", fake_exe, "image/jpeg")})
    assert response.status_code == 400

async def test_weak_password_rejected(client):
    response = await client.post("/api/auth/register", json={
        "email": "test@example.com",
        "password": "123",  # Too short
    })
    assert response.status_code == 422
```

---

## Phase 2: Auth (OAuth + Resend) Tests

| # | Test | File | Expected |
|---|------|------|----------|
| 2.1 | Register with email/password (existing flow) | `test_auth.py` | 201 |
| 2.2 | Login with email/password (existing flow) | `test_auth.py` | 200 |
| 2.3 | Google OAuth with valid token (mock) | `test_auth.py` | 200/201 |
| 2.4 | Google OAuth with invalid token | `test_auth.py` | 401 |
| 2.5 | Google OAuth links existing email account | `test_auth.py` | 200, auth_provider="both" |
| 2.6 | Forgot password (existing email) | `test_auth.py` | 200 |
| 2.7 | Forgot password (non-existent email) | `test_auth.py` | 200 (same response) |
| 2.8 | Reset password with valid token | `test_auth.py` | 200 |
| 2.9 | Reset password with expired token | `test_auth.py` | 400 |
| 2.10 | Reset password for Google-only user | `test_auth.py` | 400 |
| 2.11 | Verify email with valid token | `test_auth.py` | 200 |
| 2.12 | Verify email with expired token | `test_auth.py` | 400 |
| 2.13 | User model has new columns | `test_db.py` | Columns exist |
| 2.14 | Alembic migration up/down | Manual | Clean migration |

### Mocking Google Auth

```python
# In test fixtures
from unittest.mock import patch, AsyncMock

@pytest.fixture
def mock_google_verify():
    with patch("app.auth.oauth.verify_google_token") as mock:
        mock.return_value = {
            "google_id": "google_123456",
            "email": "testuser@gmail.com",
            "name": "Test User",
            "picture": "https://lh3.googleusercontent.com/photo.jpg",
            "email_verified": True,
        }
        yield mock
```

---

## Phase 3: Scan Pipeline Tests

| # | Test | File | Expected |
|---|------|------|----------|
| 3.1 | Scan with valid JPEG | `test_scan.py` | 200, results returned |
| 3.2 | Scan with large image (auto-resize) | `test_scan.py` | 200, processed |
| 3.3 | Scan with WebP image | `test_scan.py` | 200, converted |
| 3.4 | Scan with no hieroglyphs | `test_scan.py` | 200, "no glyphs found" |
| 3.5 | TTS endpoint calls tts_service | `test_audio.py` | Audio returned |
| 3.6 | TTS fallback chain works | `test_audio.py` | Falls to tier 2 |
| 3.7 | Progress SSE sends steps | `test_scan.py` | 4 events received |
| 3.8 | Classifier uses uint8 model | `test_core.py` | Config path correct |

---

## Phase 4: Stories Tests

| # | Test | File | Expected |
|---|------|------|----------|
| 4.1 | Story listing returns all 5 | `test_stories.py` | 5 stories |
| 4.2 | Story detail returns chapters | `test_stories.py` | 5+ chapters |
| 4.3 | Each chapter has glyph annotations | `test_stories.py` | glyphs array non-empty |
| 4.4 | Each chapter has interaction | `test_stories.py` | interaction object present |
| 4.5 | Image generation returns image | `test_stories.py` | Image bytes, WebP |
| 4.6 | Image caching works | `test_stories.py` | Second request from cache |
| 4.7 | Story progress saves to DB | `test_stories.py` | Progress retrieved |
| 4.8 | Story completion tracked | `test_stories.py` | completed=True |

---

## Phase 5: Version Promotion Tests

| # | Test | Type | Expected |
|---|------|------|----------|
| 5.1 | All routes return 200 | `test_smoke.py` | No 500s |
| 5.2 | Health check passes | `test_smoke.py` | {"status": "ok"} |
| 5.3 | Dockerfile builds | Manual | Clean build |
| 5.4 | HF Space serves on port 7860 | Manual | Page loads |
| 5.5 | All env vars loaded in production | Manual | No startup errors |

---

## Phase 6-7: Logo + Loading Tests

| # | Test | Type | Expected |
|---|------|------|----------|
| 6.1 | Logo SVG renders at 16px | Visual | Not blurry |
| 6.2 | Logo renders at 512px | Visual | Clean paths |
| 6.3 | Favicon loads in browser | Manual | Shows in tab |
| 7.1 | Loading screen appears | Visual | Overlay visible |
| 7.2 | Loading screen dismisses | Visual | Fades out < 3s |
| 7.3 | No layout shift after loading | Manual | CLS = 0 |
| 7.4 | Loading works without JS | Manual | <noscript> hides |

---

## Phase 8: Final Smoke Tests

| # | Test | Route | Expected |
|---|------|-------|----------|
| 8.1 | Landing page | `/` | 200, dual-path visible |
| 8.2 | Hieroglyphs hub | `/hieroglyphs` | 200 |
| 8.3 | Landmarks hub | `/landmarks` | 200 |
| 8.4 | Scanner | `/scan` | 200, upload works |
| 8.5 | Dictionary | `/dictionary` | 200, search works |
| 8.6 | Write | `/write` | 200, input works |
| 8.7 | Explore | `/explore` | 200, landmarks list |
| 8.8 | Chat | `/chat` | 200, Thoth responds |
| 8.9 | Stories | `/stories` | 200, 5 stories listed |
| 8.10 | Story reader | `/stories/the_eye_of_horus` | 200, chapters render |
| 8.11 | Dashboard | `/dashboard` | Auth required |
| 8.12 | Settings | `/settings` | Auth required |
| 8.13 | Register flow | Full | Account created |
| 8.14 | Google sign-in | Full | Google user created |
| 8.15 | Logout | Full | Session cleared |

---

## CI Strategy (Future)

When ready to add CI:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: pytest tests/ -v --cov=app
```

Not implementing CI now — this is for after v3 stabilizes.
