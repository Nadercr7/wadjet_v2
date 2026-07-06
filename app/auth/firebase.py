"""Firebase ID token verification (Firebase Admin SDK).

Used by the Android app: the app authenticates the user with Firebase Auth
(email/password or Google) and exchanges the resulting Firebase ID token for
an app session at POST /api/auth/firebase. Verification only needs the
Firebase project ID (public Google certs) — no service-account credentials.
"""

from __future__ import annotations

import logging

from app.config import settings

logger = logging.getLogger(__name__)

_APP_NAME = "wadjet-token-verify"


def _get_app():
    """Lazily initialize a credential-less firebase_admin app for token verification."""
    import firebase_admin

    if not settings.firebase_project_id:
        return None
    try:
        return firebase_admin.get_app(_APP_NAME)
    except ValueError:
        return firebase_admin.initialize_app(
            credential=None,
            options={"projectId": settings.firebase_project_id},
            name=_APP_NAME,
        )


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

    try:
        from firebase_admin import auth as fb_auth

        app = _get_app()
        decoded = fb_auth.verify_id_token(id_token, app=app)
    except Exception as e:  # noqa: BLE001 — any verification failure means "not authenticated"
        logger.warning("Firebase token verification failed: %s", e)
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
