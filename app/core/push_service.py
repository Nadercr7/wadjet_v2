"""E-P9: FCM push sender.

Reads device tokens from Firestore (users/{uid}/fcm_tokens — written by the
Android app, see Wadjet-Android FcmTokenRegistrar) and sends notifications via
the Firebase Admin SDK. Dead tokens (device uninstalled/rotated) are pruned.

Requires GOOGLE_APPLICATION_CREDENTIALS (service account) — Firestore reads
and FCM sends are privileged operations, unlike the token *verification* in
app/auth/firebase.py which works credential-less.
"""

from __future__ import annotations

import logging
from functools import partial

import anyio

from app.config import settings

logger = logging.getLogger(__name__)

_APP_NAME = "wadjet-push"

# FCM multicast hard limit per request
_BATCH_SIZE = 500


def _chunk(items: list, size: int = _BATCH_SIZE) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _should_prune(exception) -> bool:
    """True when FCM says the token is permanently dead (not a transient error)."""
    if exception is None:
        return False
    from firebase_admin import messaging

    if isinstance(exception, messaging.UnregisteredError):
        return True
    # invalid-argument = malformed/never-valid token
    return getattr(exception, "code", "") == "invalid-argument"


def _get_admin_app():
    import firebase_admin

    try:
        return firebase_admin.get_app(_APP_NAME)
    except ValueError:
        return firebase_admin.initialize_app(
            options={"projectId": settings.firebase_project_id},
            name=_APP_NAME,
        )


def _send_sync(
    uid: str | None,
    broadcast: bool,
    title: str,
    body: str,
    data: dict[str, str],
) -> dict:
    from firebase_admin import firestore, messaging

    app = _get_admin_app()
    db = firestore.client(app)

    if broadcast:
        docs = db.collection_group("fcm_tokens").stream()
    else:
        docs = (
            db.collection("users").document(uid).collection("fcm_tokens").stream()
        )
    token_refs = [(doc.id, doc.reference) for doc in docs]
    if not token_refs:
        return {"tokens": 0, "sent": 0, "failed": 0, "pruned": 0}

    sent = failed = pruned = 0
    for batch in _chunk(token_refs):
        message = messaging.MulticastMessage(
            tokens=[token for token, _ in batch],
            notification=messaging.Notification(title=title, body=body),
            data=data,
        )
        response = messaging.send_each_for_multicast(message, app=app)
        sent += response.success_count
        failed += response.failure_count
        for (token, ref), result in zip(batch, response.responses):
            if not result.success and _should_prune(result.exception):
                try:
                    ref.delete()
                    pruned += 1
                    logger.info("Pruned dead FCM token %s…", token[:12])
                except Exception as e:  # noqa: BLE001 — pruning is best-effort
                    logger.warning("Failed to prune token %s…: %s", token[:12], e)

    logger.info(
        "Push %s: %d tokens, %d sent, %d failed, %d pruned",
        "broadcast" if broadcast else f"to {uid}",
        len(token_refs), sent, failed, pruned,
    )
    return {"tokens": len(token_refs), "sent": sent, "failed": failed, "pruned": pruned}


async def send_push(
    *,
    uid: str | None,
    broadcast: bool,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
) -> dict:
    """Send a notification to one user's devices (uid) or all devices (broadcast)."""
    return await anyio.to_thread.run_sync(
        partial(_send_sync, uid, broadcast, title, body, data or {})
    )
