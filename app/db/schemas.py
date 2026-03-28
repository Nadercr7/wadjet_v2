"""Pydantic request/response schemas for auth and user endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    preferred_lang: str
    tier: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard / Settings ──

class UpdateProfileRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=100)
    preferred_lang: str | None = Field(default=None, pattern=r"^(en|ar)$")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class FavoriteRequest(BaseModel):
    item_type: str = Field(pattern=r"^(landmark|glyph|story)$")
    item_id: str = Field(min_length=1, max_length=200)


class StoryProgressRequest(BaseModel):
    story_id: str = Field(min_length=1, max_length=50)
    chapter_index: int = Field(ge=0)
    glyphs_learned: str = "[]"
    score: int = Field(default=0, ge=0)
    completed: bool = False
