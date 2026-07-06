"""Push API — admin-triggered FCM notifications (E-P9).

Sends to the device tokens the Android app registers under
users/{uid}/fcm_tokens. story_id / landmark_slug ride along as data so the
app's existing notification deep links open the right screen (B-01).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.config import settings
from app.db.database import get_db
from app.db.models import User
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/push", tags=["push"])


class PushSendRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=500)
    uid: str | None = Field(default=None, max_length=128, description="Target user id")
    broadcast: bool = False
    story_id: str | None = Field(default=None, max_length=100)
    landmark_slug: str | None = Field(default=None, max_length=100)


@router.post("/send")
@limiter.limit("10/minute")
async def send_push_notification(
    body: PushSendRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Admin-only: send an FCM notification to one user or broadcast to all devices."""
    if user.email != settings.admin_email:
        raise HTTPException(status_code=403, detail="Admin access only")
    if not body.broadcast and not body.uid:
        raise HTTPException(status_code=400, detail="Provide uid or broadcast=true")
    if not settings.firebase_project_id:
        raise HTTPException(status_code=503, detail="Push not configured (FIREBASE_PROJECT_ID)")

    data = {
        key: value
        for key, value in {"story_id": body.story_id, "landmark_slug": body.landmark_slug}.items()
        if value
    }

    from app.core.push_service import send_push

    try:
        result = await send_push(
            uid=body.uid,
            broadcast=body.broadcast,
            title=body.title,
            body=body.body,
            data=data,
        )
    except Exception as e:  # noqa: BLE001 — surface as service-unavailable, not a 500 trace
        logger.error("Push send failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Push unavailable (is GOOGLE_APPLICATION_CREDENTIALS configured?)",
        ) from None

    return result
