"""
Wadjet AI — File Upload Security.

Validates uploaded images before they enter the identification pipeline.

Security checks:
1. File extension whitelist (jpg, jpeg, png, webp)
2. MIME type verification via magic bytes
3. Max file size enforcement (from Settings.max_upload_size_bytes)
4. Filename sanitisation (strips path traversal / dangerous chars)
5. Temp-file lifecycle with automatic cleanup
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path, PurePosixPath

from fastapi import HTTPException, UploadFile, status

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".jpg", ".jpeg", ".png", ".webp"})

# Magic-byte signatures for accepted image formats.
# Each tuple: (offset, bytes_sequence)
_MAGIC_BYTES: dict[str, list[tuple[int, bytes]]] = {
    ".jpg": [(0, b"\xff\xd8\xff")],
    ".jpeg": [(0, b"\xff\xd8\xff")],
    ".png": [(0, b"\x89PNG\r\n\x1a\n")],
    ".webp": [(0, b"RIFF"), (8, b"WEBP")],
}

# Minimum sensible image size (an empty or truncated file < 100 bytes is unlikely valid)
_MIN_IMAGE_BYTES = 100


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sanitise_filename(raw: str) -> str:
    """Return a safe filename free of path-traversal or dangerous characters.

    * Strips directory components (``..``, ``/``, ``\\``).
    * Removes non-alphanumeric / non-basic-punctuation characters.
    * Falls back to a UUID-based name if nothing useful remains.
    """
    # Take only the final component
    name = PurePosixPath(raw.replace("\\", "/")).name

    # Strip anything that isn't alphanum, dash, underscore, or dot
    name = re.sub(r"[^\w.\-]", "_", name)

    # Collapse consecutive underscores / dots
    name = re.sub(r"[_.]{2,}", "_", name)

    # Strip leading dots (hidden files)
    name = name.lstrip(".")

    if not name or name == "_":
        ext = PurePosixPath(raw).suffix.lower()
        ext = ext if ext in ALLOWED_EXTENSIONS else ".jpg"
        name = f"{uuid.uuid4().hex}{ext}"

    return name


def _validate_extension(filename: str) -> str:
    """Validate and return the lower-cased extension.

    Raises ``HTTPException(415)`` if the extension is not whitelisted.
    """
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail={
                "error": True,
                "code": "UNSUPPORTED_FILE_TYPE",
                "message": (
                    f"File type '{ext or 'unknown'}' is not supported. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ),
            },
        )
    return ext


def _validate_magic_bytes(header: bytes, ext: str) -> None:
    """Verify that the first bytes match the expected magic signature.

    Raises ``HTTPException(415)`` on mismatch (possible spoofed extension).
    """
    signatures = _MAGIC_BYTES.get(ext, [])
    for offset, magic in signatures:
        if header[offset : offset + len(magic)] != magic:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail={
                    "error": True,
                    "code": "INVALID_FILE_CONTENT",
                    "message": (
                        "File content does not match its extension. "
                        "The file may be corrupted or mislabelled."
                    ),
                },
            )


def _validate_file_size(size: int, max_bytes: int) -> None:
    """Enforce minimum and maximum file size.

    Raises ``HTTPException(413)`` when the file is too large and
    ``HTTPException(400)`` when the file is suspiciously small.
    """
    if size > max_bytes:
        max_mb = max_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "error": True,
                "code": "FILE_TOO_LARGE",
                "message": f"File size exceeds the {max_mb:.0f} MB limit.",
            },
        )
    if size < _MIN_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": True,
                "code": "FILE_TOO_SMALL",
                "message": "File is too small to be a valid image.",
            },
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def validate_upload(
    file: UploadFile,
    *,
    max_bytes: int,
) -> bytes:
    """Run all security checks on an uploaded file and return its raw bytes.

    Parameters
    ----------
    file:
        The ``UploadFile`` from FastAPI's multipart handler.
    max_bytes:
        Maximum allowed size in bytes (from ``Settings.max_upload_size_bytes``).

    Returns
    -------
    bytes
        The validated raw image bytes, ready for preprocessing.

    Raises
    ------
    HTTPException
        400 — file too small / missing filename
        413 — file too large
        415 — disallowed extension or magic-byte mismatch
    """
    # 1. Filename must exist
    filename = file.filename or ""
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": True,
                "code": "MISSING_FILENAME",
                "message": "Uploaded file has no filename.",
            },
        )

    # 2. Sanitise + validate extension
    safe_name = sanitise_filename(filename)
    ext = _validate_extension(safe_name)

    # 3. Read contents (bounded by max_bytes + 1 to detect overflow)
    contents = await file.read(max_bytes + 1)

    # 4. Size checks
    _validate_file_size(len(contents), max_bytes)

    # 5. Magic-byte verification
    _validate_magic_bytes(contents, ext)

    return contents


async def save_to_temp(
    data: bytes,
    *,
    suffix: str = ".jpg",
) -> Path:
    """Write validated image bytes to a temporary file **asynchronously**.

    Uses :func:`app.core.async_file.async_save_to_temp` under the hood
    so the event loop is never blocked.

    The caller is responsible for deleting the file when done
    (or use :func:`cleanup_temp` / :func:`app.core.async_file.async_temp_file`).

    Returns the ``Path`` to the temp file.
    """
    from app.core.async_file import async_save_to_temp

    return await async_save_to_temp(data, suffix=suffix)


async def cleanup_temp(path: Path | str) -> None:
    """Silently remove a temporary file if it exists (non-blocking)."""
    from app.core.async_file import async_cleanup_temp

    await async_cleanup_temp(path)
