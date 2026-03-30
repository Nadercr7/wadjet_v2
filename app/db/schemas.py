"""Pydantic request/response schemas for auth and user endpoints."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


def _validate_password_complexity(password: str) -> str:
    """Enforce password complexity: 8+ chars, 1 upper, 1 lower, 1 digit."""
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one digit")
    return password


# ── Auth ──

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class GoogleAuthRequest(BaseModel):
    credential: str = Field(min_length=1, max_length=4096)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    preferred_lang: str
    tier: str
    auth_provider: str = "email"
    email_verified: bool = False
    avatar_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard / Settings ──

class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    preferred_lang: Literal["en", "ar"] | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        return _validate_password_complexity(v)


class FavoriteRequest(BaseModel):
    item_type: str = Field(pattern=r"^(landmark|glyph|story)$")
    item_id: str = Field(min_length=1, max_length=200)


class StoryProgressRequest(BaseModel):
    story_id: str = Field(min_length=1, max_length=50)
    chapter_index: int = Field(ge=0)
    glyphs_learned: str = Field("[]", max_length=5000)
    score: int = Field(default=0, ge=0)
    completed: bool = False
