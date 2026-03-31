"""Google OAuth ID token verification."""

from __future__ import annotations

import logging

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from app.config import settings

logger = logging.getLogger(__name__)

# Reusable transport for Google token verification
_google_request = google_requests.Request()


def verify_google_token(credential: str) -> dict | None:
    """Verify a Google Sign-In ID token and return user info.

    Returns dict with keys: sub, email, name, picture, email_verified
    or None if verification fails.
    """
    if not settings.google_client_id:
        logger.error("GOOGLE_CLIENT_ID not configured")
        return None

    try:
        idinfo = id_token.verify_oauth2_token(
            credential,
            _google_request,
            settings.google_client_id,
        )
        # Verify issuer
        if idinfo.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            logger.warning("Invalid issuer in Google token: %s", idinfo.get("iss"))
            return None

        return {
            "sub": idinfo["sub"],
            "email": idinfo.get("email", ""),
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "email_verified": idinfo.get("email_verified", False),
        }
    except ValueError as e:
        logger.warning("Google token verification failed: %s", e)
        return None
    except Exception as e:
        logger.error("Google token verification error: %s", e)
        return None
