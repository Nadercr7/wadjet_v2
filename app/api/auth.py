"""Auth API — register, login, refresh, logout."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import create_access_token, create_refresh_token, decode_token
from app.auth.password import hash_password, verify_password
from app.db.crud import (
    create_user,
    delete_refresh_token,
    delete_user_refresh_tokens,
    get_user_by_email,
    store_refresh_token,
    validate_refresh_token,
)
from app.db.database import get_db
from app.db.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_COOKIE = "wadjet_refresh"
REFRESH_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=False,  # Set True in production (HTTPS)
        samesite="lax",
        max_age=REFRESH_MAX_AGE,
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE, path="/api/auth")


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(body: RegisterRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    pw_hash = hash_password(body.password)
    user = await create_user(db, email=body.email, password_hash=pw_hash, display_name=body.display_name)

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
    return response


@router.post("/login")
@limiter.limit("10/minute")
async def login(body: LoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Log in with email and password, receive tokens."""
    user = await get_user_by_email(db, body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

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
async def logout(request: Request, db: AsyncSession = Depends(get_db)):
    """Invalidate the refresh token and clear the cookie."""
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        await delete_refresh_token(db, token)

    response = JSONResponse(content={"detail": "Logged out"})
    _clear_refresh_cookie(response)
    return response
