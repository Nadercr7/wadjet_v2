"""Firebase ID token verification.

Used by the Android app: the app authenticates the user with Firebase Auth
(email/password or Google) and exchanges the resulting Firebase ID token for
an app session at POST /api/auth/firebase.

Two verification paths, chosen deterministically at startup:
- GOOGLE_APPLICATION_CREDENTIALS set → Firebase Admin SDK (adds revocation
  checking capability).
- Otherwise → stateless verification via google-auth's verify_firebase_token
  (Google public certs; needs only FIREBASE_PROJECT_ID — no service account,
  which matters on HF Spaces).
"""

from __future__ import annotations

import logging
import os

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from app.config import settings

logger = logging.getLogger(__name__)

_APP_NAME = "wadjet-token-verify"

# Reusable transport for cert fetching (same pattern as app/auth/oauth.py)
_google_request = google_requests.Request()


def _use_admin_sdk() -> bool:
    return bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))


def _verify_with_admin_sdk(token: str) -> dict | None:
    import firebase_admin
    from firebase_admin import auth as fb_auth

    try:
        app = firebase_admin.get_app(_APP_NAME)
    except ValueError:
        app = firebase_admin.initialize_app(
            options={"projectId": settings.firebase_project_id},
            name=_APP_NAME,
        )
    try:
        return fb_auth.verify_id_token(token, app=app)
    except Exception as e:  # noqa: BLE001 — any verification failure means "not authenticated"
        logger.warning("Firebase token verification failed (admin sdk): %s", e)
        return None


def _verify_with_public_certs(token: str) -> dict | None:
    """Verify signature/expiry/audience against Google's securetoken certs."""
    try:
        decoded = google_id_token.verify_firebase_token(
            token, _google_request, audience=settings.firebase_project_id
        )
    except ValueError as e:
        logger.warning("Firebase token verification failed: %s", e)
        return None
    except Exception as e:  # noqa: BLE001
        logger.error("Firebase token verification error: %s", e)
        return None

    if not decoded:
        return None
    expected_iss = f"https://securetoken.google.com/{settings.firebase_project_id}"
    if decoded.get("iss") != expected_iss:
        logger.warning("Invalid issuer in Firebase token: %s", decoded.get("iss"))
        return None
    if not decoded.get("sub"):
        logger.warning("Firebase token has no subject")
        return None
    return decoded


def verify_firebase_token(id_token: str) -> dict | None:
    """Verify a Firebase-issued ID token and return user info.

    Returns dict with keys: uid, email, email_verified, name, picture,
    provider (Firebase sign_in_provider, e.g. "password" / "google.com"),
    google_sub (the Google account id when the user signed in with Google),
    or None if verification fails or FIREBASE_PROJECT_ID is not configured.
    """
    if not settings.firebase_project_id:
        logger.error("FIREBASE_PROJECT_ID not configured")
        return None

    decoded = (
        _verify_with_admin_sdk(id_token)
        if _use_admin_sdk()
        else _verify_with_public_certs(id_token)
    )
    if not decoded:
        return None

    firebase_claims = decoded.get("firebase", {}) or {}
    identities = firebase_claims.get("identities", {}) or {}
    google_ids = identities.get("google.com") or []

    return {
        "uid": decoded.get("uid") or decoded.get("sub"),
        "email": decoded.get("email", ""),
        "email_verified": decoded.get("email_verified", False),
        "name": decoded.get("name"),
        "picture": decoded.get("picture"),
        "provider": firebase_claims.get("sign_in_provider"),
        "google_sub": str(google_ids[0]) if google_ids else None,
    }
