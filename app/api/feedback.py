"""Beta feedback API — collect user recommendations, bugs, and praise."""

from __future__ import annotations

import logging

import bleach
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.database import get_db
from app.db.models import Feedback, User
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

VALID_CATEGORIES = {"bug", "suggestion", "praise", "other"}


def _sanitize(v: str) -> str:
    """Strip ALL HTML tags via bleach (zero allowed tags) and normalize whitespace."""
    return bleach.clean(v, tags=[], attributes={}, strip=True).strip()


class FeedbackRequest(BaseModel):
    category: str = Field(..., min_length=1, max_length=20)
    message: str = Field(..., min_length=10, max_length=1000)
    page_url: str = Field(default="", max_length=200)
    name: str = Field(default="", max_length=100)
    email: str = Field(default="", max_length=200)

    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in VALID_CATEGORIES:
            raise ValueError(f"Category must be one of: {', '.join(VALID_CATEGORIES)}")
        return v

    @field_validator("message")
    @classmethod
    def sanitize_message(cls, v: str) -> str:
        return _sanitize(v)

    @field_validator("name", "email")
    @classmethod
    def strip_fields(cls, v: str) -> str:
        return _sanitize(v)


@router.post("")
@limiter.limit("5/minute")
async def submit_feedback(
    request: Request,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    ua = request.headers.get("User-Agent", "")[:500]
    entry = Feedback(
        category=body.category,
        message=body.message,
        page_url=body.page_url[:200] if body.page_url else "",
        name=body.name[:100] if body.name else "",
        email=body.email[:200] if body.email else "",
        user_agent=ua,
    )
    db.add(entry)
    await db.commit()
    logger.info("Feedback #%s (%s) from %s", entry.id, body.category, body.page_url)
    return JSONResponse({"ok": True, "id": entry.id}, status_code=201)


@router.get("")
async def list_feedback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
):
    if user.email != settings.admin_email:
        raise HTTPException(status_code=403, detail="Admin access only")
    limit = min(limit, 200)
    offset = max(offset, 0)
    result = await db.execute(
        select(Feedback).order_by(Feedback.created_at.desc()).offset(offset).limit(limit)
    )
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "category": r.category,
            "message": r.message,
            "page_url": r.page_url,
            "name": r.name,
            "email": r.email,
            "user_agent": r.user_agent,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
