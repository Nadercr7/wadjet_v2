# Phase 1 — Security Hardening

## Goal
Fix all critical and high-priority security vulnerabilities. After this phase, the app has production-grade input validation, CSRF protection, rate limiting, and no information leakage.

## Bugs Fixed
- **C2**: Content-Type bypass allows non-image uploads
- **C3**: Quiz answers exposed in client-side JavaScript
- **C5**: Internal error messages leaked to users
- **C6**: No CSRF protection on POST endpoints
- **H3**: Static quiz dedup loop can infinite-loop
- **H6**: No rate limiting on any endpoints
- **M14**: Deterministic quiz seed → same distractors every time

## Files Modified
- `requirements.txt` — add slowapi, starlette-csrf
- `app/main.py` — add CSRF middleware, rate limiter init
- `app/api/scan.py` — magic byte validation, error sanitization
- `app/api/chat.py` — error sanitization
- `app/api/quiz.py` — server-only answer verification
- `app/api/write.py` — error sanitization
- `app/api/translate.py` — error sanitization
- `app/api/explore.py` — error sanitization
- `app/core/quiz_engine.py` — fix dedup loop, use secrets.choice
- `app/templates/quiz.html` — remove _correct from client state

## Implementation Steps

### Step 1: Install security dependencies
```bash
# Add to requirements.txt:
slowapi>=0.1.9
starlette-csrf>=3.0.0
```

### Step 2: Fix C2 — Magic byte validation in scan.py
Replace the content-type check with magic byte validation:
```python
# Magic byte signatures
MAGIC_BYTES = {
    b'\xff\xd8\xff': 'image/jpeg',
    b'\x89PNG': 'image/png',
    b'RIFF': 'image/webp',  # WebP starts with RIFF....WEBP
}

async def _read_image_bytes(file: UploadFile) -> tuple[bytes, np.ndarray]:
    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10 MB.")

    # Validate magic bytes (not just content-type header which can be spoofed)
    valid = False
    for magic, mime in MAGIC_BYTES.items():
        if data[:len(magic)] == magic:
            if magic == b'RIFF' and data[8:12] != b'WEBP':
                continue  # RIFF but not WebP
            valid = True
            break
    if not valid:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Use JPEG, PNG, or WebP.",
        )

    arr = np.frombuffer(data, np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Could not decode image.")
    return data, image
```

### Step 3: Fix C3 — Remove quiz answers from client
In `quiz.html`, remove the `_correct` field from the Alpine data. All answer checking goes through the server:
```javascript
// BEFORE (insecure):
// q._correct stored client-side, used in offline fallback

// AFTER (secure):
// Offline: hash correct answer with HMAC, send hash to client
// Client sends answer + hash back to server-side check
// Even offline, answers verified via hash comparison
```

In `quiz.py`, add a signed hash endpoint:
```python
import hashlib, hmac
QUIZ_SECRET = os.urandom(32)  # Generated once at startup

def sign_answer(answer: str) -> str:
    return hmac.new(QUIZ_SECRET, answer.encode(), hashlib.sha256).hexdigest()
```

### Step 4: Fix C5 — Error sanitization
Wrap all router handlers with try/except that logs detailed errors but returns generic messages:
```python
except Exception as e:
    logger.error(f"Scan failed: {e}", exc_info=True)
    raise HTTPException(status_code=500, detail="An error occurred processing your request.")
```

### Step 5: Fix C6 — CSRF middleware
In `main.py`:
```python
from starlette_csrf import CSRFMiddleware
app.add_middleware(CSRFMiddleware, secret=settings.csrf_secret)
```

### Step 6: Fix H6 — Rate limiting
In `main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

Per-endpoint decorators:
```python
@router.post("/api/scan")
@limiter.limit("30/minute")
async def scan(request: Request, ...):
```

### Step 7: Fix H3 — Quiz dedup guard
In `quiz_engine.py`, add max iteration:
```python
MAX_DEDUP_ATTEMPTS = 100
attempts = 0
while question_id in seen and attempts < MAX_DEDUP_ATTEMPTS:
    question_id = random.choice(pool)
    attempts += 1
```

### Step 8: Fix M14 — Use secrets for quiz randomization
```python
import secrets
# Replace random.choice with secrets.choice for question selection
# Keep random.seed only for reproducible distractor sets within a single question
```

## Testing Checklist
- [ ] Upload `.exe` renamed to `.jpg` → returns 400 "Unsupported file type"
- [ ] Upload file with `Content-Type: image/jpeg` but PNG magic bytes → accepts correctly (magic bytes win)
- [ ] Upload file with `Content-Type: None` → magic byte check still works
- [ ] View quiz HTML source → no `_correct` or answer text visible
- [ ] Quiz works online: answer checked by server, correct/incorrect shown
- [ ] Quiz works offline: hash comparison, no answer leakage
- [ ] Send 35 scan requests in 1 minute → last 5 return 429 Too Many Requests
- [ ] Force server error → user sees "An error occurred", server logs show full traceback
- [ ] CSRF token present in all forms, POST without token → 403
- [ ] Run quiz 10 times → distractors vary (not deterministic)
- [ ] Quiz dedup: request 1000 questions → no hang/infinite loop

## Git Commit
```
[Phase 1] Security hardening — CSRF, rate limiting, magic bytes, error sanitization, quiz fixes
```
