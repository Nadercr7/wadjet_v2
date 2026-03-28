"""
Wadjet AI — Async File Pipeline.

Provides fully non-blocking file I/O for the image identification pipeline:
    Upload → async save to temp → async read for model → async cleanup

All operations use ``aiofiles`` so they never block the event loop.
"""

from __future__ import annotations

import contextlib
import tempfile
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import aiofiles
import aiofiles.os

from app.core.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = get_logger("wadjet.async_file")


# ---------------------------------------------------------------------------
# Async temp-file write
# ---------------------------------------------------------------------------


async def async_save_to_temp(
    data: bytes,
    *,
    suffix: str = ".jpg",
    prefix: str = "wadjet_",
) -> Path:
    """Write *data* to a new temporary file **without blocking** the event loop.

    Parameters
    ----------
    data:
        Raw bytes to persist (typically a validated image).
    suffix:
        File extension for the temp file (default ``.jpg``).
    prefix:
        Filename prefix (default ``wadjet_``).

    Returns
    -------
    Path
        Absolute path to the created temp file.  The caller is responsible
        for deletion—use :func:`async_cleanup_temp` or
        :class:`async_temp_file`.
    """
    # Build a unique path inside the system temp directory.
    tmp_dir = Path(tempfile.gettempdir())
    unique = uuid.uuid4().hex[:12]
    tmp_path = tmp_dir / f"{prefix}{unique}{suffix}"

    async with aiofiles.open(tmp_path, "wb") as fh:
        await fh.write(data)

    logger.debug("temp_file_saved", path=str(tmp_path), size=len(data))
    return tmp_path


# ---------------------------------------------------------------------------
# Async file read
# ---------------------------------------------------------------------------


async def async_read_file(path: Path | str) -> bytes:
    """Read an entire file asynchronously and return its contents.

    Parameters
    ----------
    path:
        File to read.

    Returns
    -------
    bytes
        Raw file contents.

    Raises
    ------
    FileNotFoundError
        If the target file does not exist.
    """
    target = Path(path)
    if not target.is_file():
        msg = f"File not found: {target}"
        raise FileNotFoundError(msg)

    async with aiofiles.open(target, "rb") as fh:
        contents = await fh.read()

    logger.debug("file_read", path=str(target), size=len(contents))
    return contents


# ---------------------------------------------------------------------------
# Async cleanup
# ---------------------------------------------------------------------------


async def async_cleanup_temp(path: Path | str) -> bool:
    """Delete a temporary file without blocking.

    Returns ``True`` if the file was removed, ``False`` if it was already
    gone or removal failed (errors are silently suppressed).
    """
    target = Path(path)
    with contextlib.suppress(OSError):
        await aiofiles.os.remove(target)
        logger.debug("temp_file_cleaned", path=str(target))
        return True
    return False


# ---------------------------------------------------------------------------
# Async context manager — full lifecycle
# ---------------------------------------------------------------------------


@contextlib.asynccontextmanager
async def async_temp_file(
    data: bytes,
    *,
    suffix: str = ".jpg",
    prefix: str = "wadjet_",
) -> AsyncIterator[Path]:
    """Context manager that writes *data* to a temp file and guarantees cleanup.

    Usage::

        async with async_temp_file(image_bytes, suffix=".png") as tmp_path:
            result = await process(tmp_path)
        # tmp_path is deleted automatically here

    Yields
    ------
    Path
        Path to the temp file containing *data*.
    """
    tmp_path = await async_save_to_temp(data, suffix=suffix, prefix=prefix)
    try:
        yield tmp_path
    finally:
        await async_cleanup_temp(tmp_path)
