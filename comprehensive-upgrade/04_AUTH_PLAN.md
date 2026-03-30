# AUTH PLAN — Google OAuth + Resend Email Integration

> Deep-dive: data model changes, endpoint specs, security considerations, UI changes.

---

## Current Auth Architecture

### Endpoints
| Method | Path | Auth | Rate Limit | Purpose |
|--------|------|------|------------|---------|
| POST | `/api/auth/register` | Public | 5/min | Create account (email+password) |
| POST | `/api/auth/login` | Public | 10/min | Login (email+password) |
| POST | `/api/auth/refresh` | Cookie | — | Rotate refresh token |
| POST | `/api/auth/logout` | Cookie | — | Invalidate refresh token |

### Token Strategy
- **Access token**: JWT HS256, 30 min TTL, stored in JS memory
- **Refresh token**: Random string, 7-day TTL, stored in DB, sent as HttpOnly cookie
- **Session cookie**: `wadjet_session=1`, non-HttpOnly, 30 days (for JS to know "logged in")

### User Model (Current)
```python
class User(Base):
    id            = Column(String, primary_key=True)  # uuid4 hex
    email         = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name  = Column(String, nullable=True)
    preferred_lang = Column(String, default="en")
    tier          = Column(String, default="free")
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

## Data Model Changes

### New User Columns

```python
# Add to User model in app/db/models.py
google_id       = Column(String, unique=True, nullable=True, index=True)
auth_provider   = Column(String, default="email")     # "email", "google", "both"
email_verified  = Column(Boolean, default=False)
avatar_url      = Column(String, nullable=True)        # Google profile picture URL
```

### Alembic Migration

```python
# alembic/versions/xxxx_add_oauth_columns.py
def upgrade():
    op.add_column("users", sa.Column("google_id", sa.String(), nullable=True))
    op.add_column("users", sa.Column("auth_provider", sa.String(), server_default="email"))
    op.add_column("users", sa.Column("email_verified", sa.Boolean(), server_default=sa.false()))
    op.add_column("users", sa.Column("avatar_url", sa.String(), nullable=True))
    op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)
    
    # Make password_hash nullable (Google-only users have no password)
    # SQLite doesn't support ALTER COLUMN, so we need batch mode
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("password_hash", nullable=True)

def downgrade():
    op.drop_index("ix_users_google_id")
    op.drop_column("users", "avatar_url")
    op.drop_column("users", "email_verified")
    op.drop_column("users", "auth_provider")
    op.drop_column("users", "google_id")
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("password_hash", nullable=False)
```

### New Table: Email Verification Tokens

```python
class EmailToken(Base):
    __tablename__ = "email_tokens"
    
    id         = Column(Integer, primary_key=True, autoincrement=True)
    user_id    = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    token_type = Column(String, nullable=False)  # "verification" or "reset"
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
```

---

## New Endpoints

### POST `/api/auth/google`

Google Sign-In callback. Receives credential from Google's JS library.

```
Request:  { "credential": "<Google ID token>" }
Response: { "access_token": "...", "token_type": "bearer", "user": {...}, "is_new": true/false }
```

**Flow**:
1. Verify Google ID token with `google.oauth2.id_token.verify_oauth2_token()`
2. Extract: email, sub (Google ID), name, picture
3. Check if user exists by `google_id`:
   - **Yes**: Login (create tokens, return user)
   - **No**: Check by email:
     - **Email exists**: Link Google account (set `google_id`, `auth_provider="both"`)
     - **Email not found**: Create new user (`auth_provider="google"`, `password_hash=None`, `email_verified=True`)
4. Set refresh cookie, return access token

### POST `/api/auth/verify-email`

```
Request:  { "token": "<6-char code or URL token>" }
Response: { "message": "Email verified" }
```

### POST `/api/auth/forgot-password`

```
Request:  { "email": "user@example.com" }
Response: { "message": "If that email exists, a reset link has been sent" }
```

**Always returns 200** — never reveals if email exists.

### POST `/api/auth/reset-password`

```
Request:  { "token": "<reset token>", "password": "<new password>" }
Response: { "message": "Password reset successful" }
```

---

## New Files

### `app/auth/oauth.py`

```python
"""Google OAuth token verification."""
from google.oauth2 import id_token
from google.auth.transport import requests
from app.config import settings

async def verify_google_token(credential: str) -> dict:
    """Verify Google ID token and return user info.
    
    Returns dict with: sub, email, name, picture, email_verified
    Raises ValueError on invalid token.
    """
    idinfo = id_token.verify_oauth2_token(
        credential,
        requests.Request(),
        settings.google_client_id,
    )
    
    if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
        raise ValueError("Invalid issuer")
    
    return {
        "google_id": idinfo["sub"],
        "email": idinfo["email"],
        "name": idinfo.get("name", ""),
        "picture": idinfo.get("picture", ""),
        "email_verified": idinfo.get("email_verified", False),
    }
```

### `app/auth/email.py`

```python
"""Email sending via Resend for verification and password reset."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import resend
from app.config import settings

resend.api_key = settings.resend_api_key

FROM_EMAIL = "Wadjet <noreply@yourdomain.com>"  # Update with verified domain

def generate_token() -> tuple[str, str]:
    """Generate a random token and its SHA-256 hash."""
    raw = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed

async def send_verification_email(to_email: str, token: str) -> bool:
    """Send email verification link."""
    verify_url = f"{settings.base_url}/api/auth/verify-email?token={token}"
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Verify your Wadjet account",
            "html": f"""
                <h2>Welcome to Wadjet</h2>
                <p>Click the link below to verify your email:</p>
                <a href="{verify_url}">Verify Email</a>
                <p>This link expires in 24 hours.</p>
                <p style="color:#666;font-size:12px">If you didn't create an account, ignore this email.</p>
            """
        })
        return True
    except Exception:
        return False

async def send_reset_email(to_email: str, token: str) -> bool:
    """Send password reset link."""
    reset_url = f"{settings.base_url}/api/auth/reset-password?token={token}"
    try:
        resend.Emails.send({
            "from": FROM_EMAIL,
            "to": [to_email],
            "subject": "Reset your Wadjet password",
            "html": f"""
                <h2>Password Reset</h2>
                <p>Click the link below to reset your password:</p>
                <a href="{reset_url}">Reset Password</a>
                <p>This link expires in 1 hour.</p>
                <p style="color:#666;font-size:12px">If you didn't request this, ignore this email.</p>
            """
        })
        return True
    except Exception:
        return False
```

---

## Google Sign-In Client Integration

### In `base.html` `<head>`

```html
<!-- Google Sign-In (load once, globally) -->
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

### In `nav.html` (login/register area)

```html
<div id="g_id_onload"
     data-client_id="{{ settings.google_client_id }}"
     data-callback="handleGoogleCredential"
     data-auto_prompt="false">
</div>
<div class="g_id_signin"
     data-type="standard"
     data-shape="rectangular"
     data-theme="filled_black"
     data-text="signin_with"
     data-size="large"
     data-logo_alignment="left">
</div>
```

### In `app.js`

```javascript
// Google Sign-In callback
window.handleGoogleCredential = async function(response) {
    try {
        const res = await fetch('/api/auth/google', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ credential: response.credential })
        });
        const data = await res.json();
        if (res.ok) {
            Alpine.store('auth').setToken(data.access_token);
            Alpine.store('auth').setUser(data.user);
            window.location.reload();
        }
    } catch (err) {
        console.error('Google auth failed:', err);
    }
};
```

---

## Google Cloud Console Setup

### Required Configuration

1. Go to https://console.cloud.google.com/apis/credentials
2. Select the existing OAuth 2.0 Client ID (or create new)
3. Under **Authorized JavaScript origins**, add:
   - `https://nadercr7-wadjet-v2.hf.space`
   - `http://localhost:8000` (for dev)
4. Under **Authorized redirect URIs**, add:
   - `https://nadercr7-wadjet-v2.hf.space` (for popup mode)
   - `http://localhost:8000` (for dev)
5. Copy **Client Secret** → add to `.env` as `GOOGLE_CLIENT_SECRET`

### Consent Screen Configuration
- App name: **Wadjet**
- User support email: `naderelakany@gmail.com`
- Authorized domains: `hf.space`
- Logo: upload wadjet logo when ready
- Scopes: `email`, `profile`, `openid`

---

## Resend Configuration

### Setup Checklist

1. Login to https://resend.com/dashboard
2. Domains → Verify sending domain (or use `onboarding@resend.dev` for testing)
3. API Keys → Copy key → verify in `.env` as `RESEND_API_KEY`
4. Test: `curl -X POST 'https://api.resend.com/emails' -H 'Authorization: Bearer <key>' -H 'Content-Type: application/json' -d '{"from":"onboarding@resend.dev","to":"your@email.com","subject":"test","text":"hello"}'`

### Rate Limits (Free Tier)
- 100 emails/day
- 1 email/second
- Sufficient for verification + reset flows

---

## Security Considerations

| Concern | Mitigation |
|---------|-----------|
| Google token replay | Verify `aud` matches our client ID, check `iat` freshness |
| Email enumeration via forgot-password | Always return "If email exists, reset sent" |
| Reset token brute force | SHA-256 hash tokens in DB, 1-hour expiry, rate limit 3/min |
| Google-only user password reset | Check `auth_provider` — reject if "google" only |
| Account linking confusion | When Google email matches existing, link accounts (set auth_provider="both") |
| CSRF on Google callback | Google library adds `g_csrf_token` cookie — verify server-side |

---

## Dependencies to Add

```
# requirements.txt additions
google-auth>=2.29.0
resend>=2.0.0
```

---

## Test Cases

| # | Test | Expected |
|---|------|----------|
| 1 | Register with email/password | 201, tokens returned |
| 2 | Login with email/password | 200, tokens returned |
| 3 | Google sign-in (new user) | 201, user created with google_id |
| 4 | Google sign-in (existing Google user) | 200, login successful |
| 5 | Google sign-in (email exists, no Google) | 200, accounts linked |
| 6 | Forgot password (existing email) | 200, email sent |
| 7 | Forgot password (non-existent email) | 200, no email sent (same response) |
| 8 | Reset password (valid token) | 200, password changed |
| 9 | Reset password (expired token) | 400, "Token expired" |
| 10 | Reset password (Google-only user) | 400, "Account uses Google sign-in" |
| 11 | Verify email (valid token) | 200, email_verified=True |
| 12 | Verify email (expired token) | 400, "Token expired" |
| 13 | Register → verify → login | Full flow works |
| 14 | Google sign-in → logout → login again | Session maintained correctly |
