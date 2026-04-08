"""Auth API — register, login, refresh, logout, Google OAuth, email verification, password reset."""

from __future__ import annotations

import hashlib
import logging
import secrets
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password
from app.config import settings
from app.db.crud import (
    create_email_token,
    create_user,
    delete_email_token,
    delete_refresh_token,
    delete_user_refresh_tokens,
    get_user_by_email,
    get_user_by_google_id,
    link_google_account,
    store_refresh_token,
    validate_email_token,
    validate_refresh_token,
    verify_user_email,
)
from app.db.database import get_db
from app.db.schemas import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "wadjet_refresh"
REFRESH_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds

# Dummy bcrypt hash used when user doesn't exist — constant-time defence against timing oracle
_DUMMY_HASH = "$2b$12$OWl8stzx0kGvRTE254mf.ulqxl8uBqWVaGhAVb6bfXqq3Z2iF2Fay"

# ── Account lockout (SEC-015) ──
_MAX_FAILED_ATTEMPTS = 10
_LOCKOUT_SECONDS = 900  # 15 minutes
_failed_attempts: dict[str, list[float]] = defaultdict(list)


def _check_account_lockout(email: str) -> None:
    """Raise 429 if this email has exceeded max failed login attempts."""
    now = time.monotonic()
    attempts = _failed_attempts.get(email, [])
    # Prune attempts older than the lockout window
    recent = [t for t in attempts if now - t < _LOCKOUT_SECONDS]
    _failed_attempts[email] = recent
    if len(recent) >= _MAX_FAILED_ATTEMPTS:
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.")


def _record_failed_attempt(email: str) -> None:
    _failed_attempts[email].append(time.monotonic())


def _clear_failed_attempts(email: str) -> None:
    _failed_attempts.pop(email, None)


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.environment != "development",
        samesite="lax",
        max_age=REFRESH_MAX_AGE,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/auth")


SESSION_COOKIE = "wadjet_session"
SESSION_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


def _set_session_cookie(response: Response, request: Request) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value="1",
        httponly=False,
        samesite="lax",
        secure=str(request.url.scheme) == "https",
        path="/",
        max_age=SESSION_MAX_AGE,
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE, path="/")


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    email = body.email.lower().strip()
    existing = await get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    pw_hash = hash_password(body.password)
    user = await create_user(db, email=email, password_hash=pw_hash, display_name=body.display_name)

    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id)
    await store_refresh_token(db, user.id, refresh_token, expires_at)

    response = JSONResponse(
        status_code=201,
        content={
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        },
    )
    _set_refresh_cookie(response, refresh_token)
    _set_session_cookie(response, request)
    return response


@router.post("/login")
@limiter.limit("10/minute")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Log in with email and password, receive tokens."""
    email = body.email.lower().strip()

    # SEC-015: Per-account lockout check
    _check_account_lockout(email)

    user = await get_user_by_email(db, email)
    # Always run verify_password to prevent timing oracle (constant-time regardless of user existence)
    pw_hash = user.password_hash if user else _DUMMY_HASH
    password_ok = verify_password(body.password, pw_hash)
    if not user or not password_ok:
        _record_failed_attempt(email)
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Successful login — clear failed attempts
    _clear_failed_attempts(email)

    # Clean up old refresh tokens for this user before issuing a new one
    await delete_user_refresh_tokens(db, user.id)

    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id)
    await store_refresh_token(db, user.id, refresh_token, expires_at)

    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(mode="json"),
    })
    _set_refresh_cookie(response, refresh_token)
    _set_session_cookie(response, request)
    return response


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(request: Request, db: AsyncSession = Depends(get_db)):
    """Get a new access token using the refresh cookie."""
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")

    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    stored = await validate_refresh_token(db, token)
    if not stored:
        raise HTTPException(status_code=401, detail="Refresh token expired or revoked")

    # Rotate: delete old, issue new
    await delete_refresh_token(db, token)
    new_access = create_access_token(payload["sub"])
    new_refresh, expires_at = create_refresh_token(payload["sub"])
    await store_refresh_token(db, payload["sub"], new_refresh, expires_at)

    response = JSONResponse(content={
        "access_token": new_access,
        "token_type": "bearer",
    })
    _set_refresh_cookie(response, new_refresh)
    return response


@router.post("/logout")
@limiter.limit("10/minute")
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Invalidate the refresh token and clear the cookie."""
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        await delete_refresh_token(db, token)

    response = JSONResponse(content={"detail": "Logged out"})
    _clear_refresh_cookie(response)
    _clear_session_cookie(response)
    return response


# ── Helpers for email tokens ──

def _hash_email_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _issue_tokens_response(user, request: Request) -> JSONResponse:
    """Create access + refresh tokens and build a JSON response with cookies."""
    access_token = create_access_token(user.id)
    return JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(mode="json"),
    })


async def _issue_full_session(user, request: Request, db: AsyncSession) -> JSONResponse:
    """Issue access + refresh tokens with cookies set."""
    access_token = create_access_token(user.id)
    refresh_token, expires_at = create_refresh_token(user.id)
    await store_refresh_token(db, user.id, refresh_token, expires_at)

    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user).model_dump(mode="json"),
    })
    _set_refresh_cookie(response, refresh_token)
    _set_session_cookie(response, request)
    return response


# ── Google OAuth ──

@router.post("/google")
@limiter.limit("10/minute")
async def google_auth(body: GoogleAuthRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate with a Google Sign-In ID token."""
    from app.auth.oauth import verify_google_token

    google_info = verify_google_token(body.credential)
    if not google_info:
        raise HTTPException(status_code=401, detail="Invalid Google credential")

    # SEC-013: Reject unverified Google emails
    if not google_info.get("email_verified"):
        raise HTTPException(status_code=400, detail="Google email not verified")

    google_id = google_info["sub"]
    email = google_info["email"].lower().strip()

    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    try:
        # 1. Check if we already have a user with this google_id
        user = await get_user_by_google_id(db, google_id)
        if user:
            return await _issue_full_session(user, request, db)

        # 2. Check if email already exists (link accounts)
        user = await get_user_by_email(db, email)
        if user:
            user = await link_google_account(db, user, google_id, google_info.get("picture"))
            return await _issue_full_session(user, request, db)

        # 3. New user — create with Google provider
        user = await create_user(
            db,
            email=email,
            password_hash=None,
            display_name=google_info.get("name"),
            google_id=google_id,
            auth_provider="google",
            email_verified=True,  # Google emails are pre-verified
            avatar_url=google_info.get("picture"),
        )
        response = await _issue_full_session(user, request, db)
        response.status_code = 201
        return response
    except HTTPException:
        raise
    except Exception as e:
        err_type = type(e).__name__
        logger.error("Google auth DB error for %s: [%s] %s", email, err_type, e, exc_info=True)
        # Include error type in response so we can diagnose remotely
        raise HTTPException(
            status_code=500,
            detail=f"Authentication failed ({err_type}) — please try again",
        ) from None


# ── Email Verification ──

@router.post("/send-verification")
@limiter.limit("3/minute")
async def send_verification(request: Request, db: AsyncSession = Depends(get_db)):
    """Send a verification email to the current user (requires auth)."""
    from app.auth.dependencies import get_current_user
    from app.auth.email import send_verification_email

    user = await get_current_user(request, db)
    if user.email_verified:
        return JSONResponse(content={"detail": "Email already verified"})

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_email_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(hours=24)
    await create_email_token(db, user.id, token_hash, "verify", expires_at)

    send_verification_email(user.email, raw_token)
    return JSONResponse(content={"detail": "Verification email sent"})


@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email(body: VerifyEmailRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Verify email using a token from the verification email."""
    token_hash = _hash_email_token(body.token)
    stored = await validate_email_token(db, token_hash, "verify")
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    await verify_user_email(db, stored.user_id)
    await delete_email_token(db, stored.id)
    return JSONResponse(content={"detail": "Email verified successfully"})


@router.get("/verify-email")
async def verify_email_get(token: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Handle GET verification link from email (redirects to frontend)."""
    token_hash = _hash_email_token(token)
    stored = await validate_email_token(db, token_hash, "verify")
    if not stored:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/?verified=error", status_code=302)

    await verify_user_email(db, stored.user_id)
    await delete_email_token(db, stored.id)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/?verified=success", status_code=302)


# ── Password Reset ──

@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(body: ForgotPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Send a password reset email. Always returns 200 to prevent email enumeration."""
    from app.auth.email import send_password_reset_email

    email = body.email.lower().strip()
    user = await get_user_by_email(db, email)

    # Always return success to prevent email enumeration
    if not user or user.auth_provider == "google":
        return JSONResponse(content={"detail": "If an account exists, a reset email has been sent"})

    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_email_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(hours=1)
    await create_email_token(db, user.id, token_hash, "reset", expires_at)

    send_password_reset_email(user.email, raw_token)
    return JSONResponse(content={"detail": "If an account exists, a reset email has been sent"})


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(body: ResetPasswordRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Reset password using a token from the reset email."""
    from app.db.crud import get_user_by_id, update_user_password

    token_hash = _hash_email_token(body.token)
    stored = await validate_email_token(db, token_hash, "reset")
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = await get_user_by_id(db, stored.user_id)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    if user.auth_provider == "google":
        raise HTTPException(status_code=400, detail="Google-only accounts cannot set a password")

    new_hash = hash_password(body.new_password)
    await update_user_password(db, stored.user_id, new_hash)
    await delete_email_token(db, stored.id)

    # Invalidate all existing refresh tokens for security
    await delete_user_refresh_tokens(db, stored.user_id)

    return JSONResponse(content={"detail": "Password reset successfully"})
