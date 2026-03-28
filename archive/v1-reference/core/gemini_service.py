"""
Wadjet AI — Gemini Service (Base Class).

Core wrapper around the ``google-genai`` library providing:

* **Key rotation** across up to 17 API keys with automatic failover
  on 429 / quota-exceeded errors.
* **Async-first** — every public method is ``async def``.
* **Structured logging** of token usage per request.
* **Retry logic** with exponential back-off for transient errors.
* **Convenience helpers** for text generation, JSON generation,
  streaming, counting tokens, and embedding.

The service is initialised once during the FastAPI lifespan and
injected via ``Depends(get_gemini_service)``.

Phase 3.1 — foundation for all later Gemini phases.
"""

from __future__ import annotations

import asyncio
import itertools
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from app.core.exceptions import GeminiError, GeminiRateLimitError
from app.core.gemini_quota import GeminiQuotaManager
from app.core.gemini_response_cache import GeminiResponseCache

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = structlog.get_logger("wadjet.gemini")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MAX_RETRIES: int = 3
_BASE_BACKOFF_S: float = 1.0  # 1s -> 2s -> 4s


# ---------------------------------------------------------------------------
# Grounding data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class GroundingSource:
    """A single grounding citation from Google Search."""

    url: str
    title: str


@dataclass(frozen=True, slots=True)
class GroundedResponse:
    """Response from a search-grounded generation call.

    Attributes
    ----------
    text:
        Generated text enriched with real-world knowledge.
    grounding_sources:
        Web sources (URL + title) that Gemini cited.
    search_queries:
        The Google Search queries Gemini executed internally.
    """

    text: str
    grounding_sources: list[GroundingSource] = field(default_factory=list)
    search_queries: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Gemini Service
# ---------------------------------------------------------------------------


class GeminiService:
    """Async wrapper around ``google.genai.Client`` with key rotation.

    Parameters
    ----------
    api_keys:
        One or more Gemini API keys to rotate through.
    default_model:
        Model identifier for general text generation
        (default ``gemini-2.5-flash``).
    lite_model:
        Lighter model for bulk / cheaper tasks
        (default ``gemini-2.5-flash-lite``).
    embedding_model:
        Model for embedding generation
        (default ``gemini-embedding-001``).
    """

    # ── Construction ────────────────────────────

    def __init__(
        self,
        api_keys: list[str],
        *,
        default_model: str = "gemini-2.5-flash",
        lite_model: str = "gemini-2.5-flash-lite",
        embedding_model: str = "gemini-embedding-001",
    ) -> None:
        if not api_keys:
            msg = "At least one Gemini API key is required."
            raise ValueError(msg)

        self._api_keys = api_keys
        self._key_cycle = itertools.cycle(range(len(api_keys)))
        self._current_key_idx: int = next(self._key_cycle)

        # Pre-build one Client per key so rotation is instant
        self._clients: list[genai.Client] = [genai.Client(api_key=key) for key in api_keys]

        self.default_model = default_model
        self.lite_model = lite_model
        self.embedding_model = embedding_model

        # Quota manager (Phase 3.14)
        self.quota = GeminiQuotaManager()

        # Response cache (Phase 3.15)
        self.response_cache = GeminiResponseCache(max_size=1000)

        # Cumulative token counters (for monitoring)
        self._total_prompt_tokens: int = 0
        self._total_completion_tokens: int = 0
        self._total_requests: int = 0

        logger.info(
            "gemini_service_init",
            num_keys=len(api_keys),
            default_model=default_model,
            lite_model=lite_model,
            embedding_model=embedding_model,
        )

    # ── Properties ──────────────────────────────

    @property
    def available(self) -> bool:
        """Whether the service has at least one key configured."""
        return len(self._api_keys) > 0

    @property
    def stats(self) -> dict[str, Any]:
        """Return cumulative usage statistics."""
        qs = self.quota.status()
        cs = self.response_cache.stats()
        return {
            "total_requests": self._total_requests,
            "total_prompt_tokens": self._total_prompt_tokens,
            "total_completion_tokens": self._total_completion_tokens,
            "num_keys": len(self._api_keys),
            "quota_rpm_used": qs.rpm_used,
            "quota_rpm_limit": qs.rpm_limit,
            "quota_rpd_used": qs.rpd_used,
            "quota_rpd_limit": qs.rpd_limit,
            "quota_degraded": qs.is_degraded,
            "quota_blocked": qs.is_blocked,
            "cache_size": cs["size"],
            "cache_max_size": cs["max_size"],
            "cache_hits": cs["hits"],
            "cache_misses": cs["misses"],
            "cache_hit_rate": cs["hit_rate"],
        }

    # ── Key rotation ────────────────────────────

    @property
    def _client(self) -> genai.Client:
        """Return the current active client."""
        return self._clients[self._current_key_idx]

    def _rotate_key(self) -> None:
        """Advance to the next API key in the round-robin cycle."""
        prev = self._current_key_idx
        self._current_key_idx = next(self._key_cycle)
        logger.warning(
            "gemini_key_rotated",
            from_key=prev + 1,
            to_key=self._current_key_idx + 1,
        )

    # ── Token accounting ────────────────────────

    def _record_usage(
        self,
        usage: genai_types.GenerateContentResponseUsageMetadata | None,
    ) -> None:
        """Accumulate token counts from a response."""
        if usage is None:
            return
        prompt = usage.prompt_token_count or 0
        completion = usage.candidates_token_count or 0
        self._total_prompt_tokens += prompt
        self._total_completion_tokens += completion
        self._total_requests += 1
        logger.debug(
            "gemini_tokens",
            prompt_tokens=prompt,
            completion_tokens=completion,
            total_tokens=(prompt + completion),
        )

    # ── Core: generate with retry + rotation ────

    async def _generate_with_retry(
        self,
        *,
        model: str,
        contents: Any,
        config: genai_types.GenerateContentConfig | None = None,
    ) -> genai_types.GenerateContentResponse:
        """Call ``generate_content`` with retry & key rotation.

        Retries up to ``_MAX_RETRIES`` times on rate-limit (429) or
        server (5xx) errors, rotating the API key on each 429.
        """
        # Phase 3.14 — check quota before attempting
        if not self.quota.can_call():
            qs = self.quota.status()
            logger.warning(
                "gemini_quota_blocked_pre_call",
                rpm_used=qs.rpm_used,
                rpd_used=qs.rpd_used,
                message=qs.message,
            )
            raise GeminiRateLimitError(
                "AI quota limit reached. Running in fast mode — please try again shortly."
            )

        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = await self._client.aio.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
                self._record_usage(response.usage_metadata)
                self.quota.record_call()  # Phase 3.14
                return response

            except genai_errors.ClientError as exc:
                # 429 / RESOURCE_EXHAUSTED — rotate key and retry
                status = getattr(exc, "status", None) or getattr(exc, "code", None)
                exc_str = str(exc)
                is_rate_limit = (
                    status == 429
                    or str(status) == "RESOURCE_EXHAUSTED"
                    or "429" in exc_str
                    or "RESOURCE_EXHAUSTED" in exc_str
                )
                if is_rate_limit:
                    logger.warning(
                        "gemini_rate_limited",
                        attempt=attempt + 1,
                        key_index=self._current_key_idx + 1,
                    )
                    self._rotate_key()
                    last_error = exc
                    await asyncio.sleep(_BASE_BACKOFF_S * (2**attempt))
                    continue
                # Other client error — don't retry
                logger.error(
                    "gemini_client_error",
                    status=status,
                    message=str(exc),
                )
                raise GeminiError(f"Gemini API error: {exc}") from exc

            except genai_errors.ServerError as exc:
                # 5xx — retry with back-off, no key rotation
                logger.warning(
                    "gemini_server_error",
                    attempt=attempt + 1,
                    message=str(exc),
                )
                last_error = exc
                await asyncio.sleep(_BASE_BACKOFF_S * (2**attempt))
                continue

            except Exception as exc:
                logger.error("gemini_unexpected_error", error=str(exc))
                raise GeminiError(f"Unexpected Gemini error: {exc}") from exc

        # Exhausted retries
        if last_error:
            last_str = str(last_error)
            last_status = getattr(last_error, "status", None)
            if (
                last_status == 429
                or str(last_status) == "RESOURCE_EXHAUSTED"
                or "429" in last_str
                or "RESOURCE_EXHAUSTED" in last_str
            ):
                raise GeminiRateLimitError() from last_error
        raise GeminiError("Gemini service unavailable after retries.") from last_error

    # ── Public API: text generation ─────────────

    async def generate_text(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        use_cache: bool = True,
    ) -> str:
        """Generate a plain-text response.

        Returns the text of the first candidate.
        When *use_cache* is True (default), identical requests are
        served from the in-memory cache (Phase 3.15).
        """
        resolved_model = model or self.default_model

        # Phase 3.15 — cache lookup
        if use_cache:
            cached = self.response_cache.lookup(
                method="generate_text",
                prompt=prompt,
                model=resolved_model,
                system_instruction=system_instruction or "",
                temperature=str(temperature) if temperature is not None else "",
            )
            if cached is not None:
                return cached

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        response = await self._generate_with_retry(
            model=resolved_model,
            contents=prompt,
            config=config,
        )
        result = response.text or ""

        # Phase 3.15 — cache store
        if use_cache and result:
            self.response_cache.store(
                result,
                method="generate_text",
                prompt=prompt,
                model=resolved_model,
                system_instruction=system_instruction or "",
                temperature=str(temperature) if temperature is not None else "",
            )

        return result

    # ── Public API: JSON generation ─────────────

    async def generate_json(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        response_schema: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> str:
        """Generate a JSON response (``response_mime_type=application/json``).

        Returns the raw JSON string for the caller to parse.
        When *use_cache* is True, identical requests are served from cache.
        """
        resolved_model = model or self.default_model

        # Phase 3.15 — cache lookup
        if use_cache:
            cached = self.response_cache.lookup(
                method="generate_json",
                prompt=prompt,
                model=resolved_model,
                system_instruction=system_instruction or "",
                temperature=str(temperature) if temperature is not None else "",
            )
            if cached is not None:
                return cached

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_json_schema=response_schema,
        )
        response = await self._generate_with_retry(
            model=resolved_model,
            contents=prompt,
            config=config,
        )
        result = response.text or "{}"

        # Phase 3.15 — cache store
        if use_cache and result != "{}":
            self.response_cache.store(
                result,
                method="generate_json",
                prompt=prompt,
                model=resolved_model,
                system_instruction=system_instruction or "",
                temperature=str(temperature) if temperature is not None else "",
            )

        return result

    # ── Public API: multimodal (image + text) ───

    async def generate_with_image(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        *,
        model: str | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
        response_mime_type: str | None = None,
        response_schema: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> str:
        """Send an image + text prompt and return the text response.

        When *use_cache* is True, the image bytes are hashed and
        identical (image + prompt) requests are served from cache.
        """
        resolved_model = model or self.default_model
        img_hash = self.response_cache.hash_image(image_bytes) if use_cache else ""

        # Phase 3.15 — cache lookup
        if use_cache:
            cached = self.response_cache.lookup(
                method="generate_with_image",
                prompt=prompt,
                model=resolved_model,
                system_instruction=system_instruction or "",
                image_hash=img_hash,
                temperature=str(temperature) if temperature is not None else "",
            )
            if cached is not None:
                return cached

        image_part = genai_types.Part.from_bytes(
            data=image_bytes,
            mime_type=mime_type,
        )
        contents = [image_part, prompt]

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type=response_mime_type,
            response_json_schema=response_schema,
        )
        response = await self._generate_with_retry(
            model=resolved_model,
            contents=contents,
            config=config,
        )
        result = response.text or ""

        # Phase 3.15 — cache store
        if use_cache and result:
            self.response_cache.store(
                result,
                method="generate_with_image",
                prompt=prompt,
                model=resolved_model,
                system_instruction=system_instruction or "",
                image_hash=img_hash,
                temperature=str(temperature) if temperature is not None else "",
            )

        return result

    # ── Public API: streaming ───────────────────

    async def generate_text_stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """Yield text chunks as they arrive from the model.

        Note: streaming does not go through the retry loop — if the
        first call fails the caller should handle it.
        """
        # Phase 3.14 — check quota
        if not self.quota.can_call():
            raise GeminiRateLimitError(
                "AI quota limit reached. Running in fast mode — please try again shortly."
            )

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        try:
            stream = await self._client.aio.models.generate_content_stream(
                model=model or self.default_model,
                contents=prompt,
                config=config,
            )
            self.quota.record_call()  # Phase 3.14
            async for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except genai_errors.ClientError as exc:
            logger.error("gemini_stream_error", error=str(exc))
            raise GeminiError(f"Streaming error: {exc}") from exc

    # ── Public API: grounded generation (Phase 3.9) ──

    async def generate_text_grounded(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_output_tokens: int | None = None,
    ) -> GroundedResponse:
        """Generate a text response grounded with Google Search.

        Uses the Gemini Search Grounding tool (500 RPD free tier).
        Returns the response text along with source citations and
        the search queries Gemini executed internally.
        """
        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
        )
        response = await self._generate_with_retry(
            model=model or self.default_model,
            contents=prompt,
            config=config,
        )

        # Extract grounding metadata from the first candidate
        grounding_sources: list[GroundingSource] = []
        search_queries: list[str] = []

        if response.candidates:
            candidate = response.candidates[0]
            gm = getattr(candidate, "grounding_metadata", None)
            if gm:
                raw_queries = getattr(gm, "web_search_queries", None)
                if raw_queries:
                    search_queries = list(raw_queries)
                raw_chunks = getattr(gm, "grounding_chunks", None)
                if raw_chunks:
                    for chunk in raw_chunks:
                        web = getattr(chunk, "web", None)
                        if web:
                            grounding_sources.append(
                                GroundingSource(
                                    url=getattr(web, "uri", "") or "",
                                    title=getattr(web, "title", "") or "",
                                )
                            )

        logger.info(
            "gemini_grounded_response",
            sources_count=len(grounding_sources),
            queries_count=len(search_queries),
        )

        return GroundedResponse(
            text=response.text or "",
            grounding_sources=grounding_sources,
            search_queries=search_queries,
        )

    # ── Public API: count tokens ────────────────

    async def count_tokens(
        self,
        contents: str | list[Any],
        *,
        model: str | None = None,
    ) -> int:
        """Return the token count for the given contents."""
        try:
            result = await self._client.aio.models.count_tokens(
                model=model or self.default_model,
                contents=contents,
            )
            return result.total_tokens or 0
        except Exception as exc:
            logger.warning("gemini_count_tokens_error", error=str(exc))
            return 0

    # ── Public API: embeddings ──────────────────

    async def embed(
        self,
        text: str | list[str],
        *,
        model: str | None = None,
        use_cache: bool = True,
    ) -> list[list[float]]:
        """Generate embeddings for one or more texts.

        Returns a list of float vectors (one per input text).
        When *use_cache* is True, embedding results are cached for 24 h.
        """
        resolved_model = model or self.embedding_model
        # Normalise to string for cache key
        cache_prompt = text if isinstance(text, str) else "\0".join(text)

        # Phase 3.15 — cache lookup
        if use_cache:
            cached = self.response_cache.lookup_embedding(
                cache_prompt,
                model=resolved_model,
            )
            if cached is not None:
                return cached

        try:
            result = await self._client.aio.models.embed_content(
                model=resolved_model,
                contents=text,
            )
            vectors: list[list[float]] = []
            if result.embeddings:
                vectors = [e.values for e in result.embeddings if e.values]

            # Phase 3.15 — cache store
            if use_cache and vectors:
                self.response_cache.store_embedding(
                    cache_prompt,
                    vectors,
                    model=resolved_model,
                )

            return vectors
        except genai_errors.ClientError as exc:
            logger.error("gemini_embed_error", error=str(exc))
            raise GeminiError(f"Embedding error: {exc}") from exc

    # ── Public API: ping / health check ─────────

    async def ping(self) -> bool:
        """Verify that we can reach the Gemini API.

        Sends a minimal ``count_tokens`` call (cheapest operation).
        Returns ``True`` on success, ``False`` on failure.
        """
        start = time.perf_counter()
        try:
            await self._client.aio.models.count_tokens(
                model=self.default_model,
                contents="ping",
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info("gemini_ping_ok", latency_ms=round(elapsed_ms, 1))
            return True
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.warning(
                "gemini_ping_failed",
                error=str(exc),
                latency_ms=round(elapsed_ms, 1),
            )
            return False
