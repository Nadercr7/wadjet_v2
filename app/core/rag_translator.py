"""RAG Translation Engine — Gemini embeddings + few-shot bilingual translation.

Architecture:
    1. Embed query transliteration with Gemini text-embedding-004 (768-dim)
    2. FAISS search → top-k scholarly corpus examples
    3. Few-shot bilingual prompt → Gemini (EN + AR in one call)
    4. Fallback → Groq Llama 3.3 70B → Grok if Gemini rate-limited
    5. LRU cache for repeated sequences

Replaces: all-MiniLM-L6-v2 (384-dim, meaningless on MdC strings)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from app.core.ai_service import AIService, GroqService
    from app.core.gemini_service import GeminiService

try:
    import faiss

    HAS_FAISS = True
except ImportError:
    faiss = None
    HAS_FAISS = False

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EMBED_DIR = PROJECT_ROOT / "data" / "embeddings"
CORPUS_JSONL = PROJECT_ROOT / "data" / "translation" / "corpus.jsonl"


# ── Embedding via Gemini ──────────────────────────────────────────


class GeminiEmbedder:
    """Embed text using Gemini gemini-embedding-001 (768-dim via Matryoshka).

    Uses the existing GeminiService's key rotation. Falls back to
    direct API calls if no GeminiService is available.
    """

    MODEL = "gemini-embedding-001"
    DIMENSION = 768

    def __init__(self, gemini: GeminiService | None = None) -> None:
        self._gemini = gemini
        self._client = None

    def _get_client(self):
        """Get a genai client for direct embedding calls."""
        if self._client is None:
            from google import genai
            from google.genai.types import HttpOptions

            # Use first available key from GeminiService or env
            if self._gemini and self._gemini._api_keys:
                key = self._gemini._api_keys[0]
            else:
                import os

                keys = os.environ.get("GEMINI_API_KEYS", "")
                key_list = [k.strip() for k in keys.split(",") if k.strip()]
                if not key_list:
                    raise RuntimeError("No Gemini API keys for embedding")
                key = key_list[0]
            self._client = genai.Client(
                api_key=key,
                http_options=HttpOptions(timeout=30_000, api_version="v1beta"),
            )
        return self._client

    def embed(self, texts: list[str]) -> np.ndarray:
        """Embed a batch of texts synchronously. Returns (N, 768) float32 array."""
        from google.genai.types import EmbedContentConfig

        client = self._get_client()
        MAX_BATCH = 100
        all_embeddings = []

        for i in range(0, len(texts), MAX_BATCH):
            batch = texts[i : i + MAX_BATCH]
            result = client.models.embed_content(
                model=self.MODEL,
                contents=batch,
                config=EmbedContentConfig(output_dimensionality=self.DIMENSION),
            )
            for emb in result.embeddings:
                all_embeddings.append(emb.values)

        arr = np.array(all_embeddings, dtype=np.float32)
        # L2-normalize for cosine similarity with FAISS IndexFlatIP
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return arr / norms

    def embed_single(self, text: str) -> np.ndarray:
        """Embed a single text. Returns (1, 768) float32 array."""
        return self.embed([text])

    async def aembed(self, texts: list[str]) -> np.ndarray:
        """Async wrapper around sync embed (runs in executor)."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self.embed, texts)


# ── Translation Cache ─────────────────────────────────────────────


class TranslationCache:
    """Thread-safe LRU cache for translated MdC sequences."""

    def __init__(self, maxsize: int = 512) -> None:
        self._cache: OrderedDict[str, dict] = OrderedDict()
        self._maxsize = maxsize
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _key(transliteration: str) -> str:
        """Normalize and hash the transliteration."""
        normalized = transliteration.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()

    def get(self, transliteration: str) -> dict | None:
        key = self._key(transliteration)
        if key in self._cache:
            self._hits += 1
            self._cache.move_to_end(key)
            return self._cache[key].copy()
        self._misses += 1
        return None

    def put(self, transliteration: str, result: dict) -> None:
        key = self._key(transliteration)
        self._cache[key] = result
        self._cache.move_to_end(key)
        if len(self._cache) > self._maxsize:
            self._cache.popitem(last=False)

    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "maxsize": self._maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 2) if total > 0 else 0.0,
        }


# ── RAG Translator ────────────────────────────────────────────────


class RAGTranslator:
    """RAG-based Ancient Egyptian translator.

    Embedding:   Gemini text-embedding-004 (768-dim)
    Retrieval:   FAISS IndexFlatIP (inner product on L2-normalized vectors)
    Generation:  Gemini 2.5 Flash (primary) → Groq → Grok (fallbacks)
    Caching:     LRU cache (512 entries)
    """

    def __init__(
        self,
        gemini: GeminiService | None = None,
        ai_service: AIService | None = None,
        top_k: int = 5,
        cache_size: int = 512,
    ) -> None:
        self._gemini = gemini
        self._ai_service = ai_service
        self._top_k = top_k
        self._cache = TranslationCache(maxsize=cache_size)

        # Embedder
        self._embedder = GeminiEmbedder(gemini)

        # FAISS index + corpus
        self._index = None
        self._corpus: list[dict] = []
        self._load_index()

    def _load_index(self) -> None:
        """Load FAISS index and corpus IDs from disk."""
        if not HAS_FAISS:
            logger.warning("FAISS not installed — RAG retrieval disabled")
            return

        index_path = EMBED_DIR / "corpus.index"
        ids_path = EMBED_DIR / "corpus_ids.json"

        if not index_path.exists():
            logger.warning("FAISS index not found at %s — RAG disabled", index_path)
            return

        try:
            self._index = faiss.read_index(str(index_path))
            if hasattr(self._index, "nprobe"):
                self._index.nprobe = 10
            with open(ids_path, encoding="utf-8") as f:
                self._corpus = json.load(f)
            logger.info(
                "RAG index loaded: %d vectors, %d corpus entries",
                self._index.ntotal,
                len(self._corpus),
            )
        except Exception:
            logger.warning("Failed to load FAISS index", exc_info=True)
            self._index = None

    @property
    def available(self) -> bool:
        return self._index is not None and len(self._corpus) > 0

    @property
    def cache_stats(self) -> dict:
        return self._cache.stats

    # ── Retrieval ──

    def retrieve(self, transliteration: str, top_k: int | None = None) -> list[dict]:
        """Retrieve top-k similar corpus entries. Synchronous."""
        if not self.available:
            return []

        k = top_k or self._top_k
        try:
            query_vec = self._embedder.embed_single(transliteration)
            D, I = self._index.search(query_vec, k)

            results = []
            for dist, idx in zip(D[0], I[0]):
                if idx < 0 or idx >= len(self._corpus):
                    continue
                entry = self._corpus[idx].copy()
                entry["similarity"] = float(dist)
                results.append(entry)
            return results
        except Exception:
            logger.warning("RAG retrieval failed", exc_info=True)
            return []

    async def aretrieve(
        self, transliteration: str, top_k: int | None = None
    ) -> list[dict]:
        """Async retrieval — runs embedding + FAISS in executor."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.retrieve, transliteration, top_k
        )

    # ── Prompt building ──

    @staticmethod
    def _build_prompt(
        transliteration: str,
        gardiner_sequence: str,
        examples: list[dict],
    ) -> tuple[str, str]:
        """Build system prompt and user prompt for bilingual translation.

        Returns: (system_prompt, user_prompt)
        """
        system = (
            "You are an expert Egyptologist specializing in Ancient Egyptian "
            "language translation. You know the Gardiner Sign List, Manuel de "
            "Codage notation, and standard Egyptological terminology.\n\n"
            "RULES:\n"
            "- Produce a LITERAL, word-for-word translation\n"
            "- Reuse exact vocabulary from the reference examples when available\n"
            "- Do NOT paraphrase or use synonyms when an example shows the standard\n"
            "- Determinatives (marked {det:...} or <...>) are semantic, not pronounced\n"
            "- Respond ONLY with valid JSON"
        )

        parts = []

        if examples:
            parts.append(
                "REFERENCE TRANSLATIONS from a scholarly corpus "
                "(gold-standard — copy vocabulary and phrasing):\n"
            )
            for i, ex in enumerate(examples, 1):
                parts.append(
                    f"Example {i}:\n"
                    f"  MdC: {ex['transliteration']}\n"
                    f"  English: {ex['translation_en']}\n"
                )

        parts.append(
            f"\nTranslate this Ancient Egyptian inscription:\n"
            f"  MdC transliteration: {transliteration}\n"
        )
        if gardiner_sequence:
            parts.append(f"  Gardiner sequence: {gardiner_sequence}\n")

        parts.append(
            "\nProvide:\n"
            '1. "translation_en": Literal English translation (scholarly)\n'
            '2. "translation_ar": Arabic translation (Modern Standard فصحى)\n'
            '3. "context": Brief inscription type (offering formula, royal titulary, etc.)\n\n'
            "Arabic conventions:\n"
            "- God names: آمون، رع، أوزيريس، إيزيس، حورس، تحوت، أنوبيس\n"
            "- Pharaoh names: رمسيس، تحتمس، إخناتون، خوفو\n"
            "- Titles: use standard Arabic Egyptological forms\n\n"
            "Return JSON:\n"
            '{"translation_en": "...", "translation_ar": "...", "context": "..."}'
        )

        return system, "\n".join(parts)

    # ── Translation providers ──

    @staticmethod
    def _parse_json(text: str) -> dict | None:
        """Robustly parse JSON from LLM response text."""
        if not text:
            return None
        # Try direct parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try extracting JSON from markdown code block
        import re
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                pass
        # Try finding first { ... } block
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        # Handle truncated JSON — try to close it
        if start >= 0:
            fragment = text[start:].rstrip().rstrip(",")
            # Count unclosed braces and close them
            depth = fragment.count("{") - fragment.count("}")
            if depth > 0:
                fragment = fragment.rstrip(",") + "}" * depth
                try:
                    return json.loads(fragment)
                except json.JSONDecodeError:
                    pass
        return None

    async def _translate_gemini(
        self,
        transliteration: str,
        gardiner_sequence: str,
        examples: list[dict],
    ) -> dict | None:
        """Translate via Gemini JSON mode. Returns parsed dict or None."""
        if not self._gemini or not self._gemini.available:
            return None

        system, prompt = self._build_prompt(
            transliteration, gardiner_sequence, examples
        )

        try:
            result_text = await self._gemini.generate_json(
                prompt=prompt,
                system_instruction=system,
                temperature=0.2,
                max_output_tokens=2048,
            )
            if result_text:
                result = self._parse_json(result_text)
                if result and (result.get("translation_en") or result.get("translation_ar")):
                    return result
            return None
        except Exception:
            logger.warning("Gemini translation failed", exc_info=True)
            return None

    async def _translate_groq(
        self,
        transliteration: str,
        gardiner_sequence: str,
        examples: list[dict],
    ) -> dict | None:
        """Translate via Groq Llama 3.3 70B. Returns parsed dict or None."""
        if not self._ai_service:
            return None

        groq = getattr(self._ai_service, "_groq", None)
        if not groq or not groq.available:
            return None

        system, prompt = self._build_prompt(
            transliteration, gardiner_sequence, examples
        )

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            resp = await groq._chat_completion(
                messages,
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            text = groq._extract_text(resp)
            if text:
                data = self._parse_json(text)
                if data and (data.get("translation_en") or data.get("translation_ar")):
                    return data
            return None
        except Exception:
            logger.warning("Groq translation failed", exc_info=True)
            return None

    async def _translate_grok(
        self,
        transliteration: str,
        gardiner_sequence: str,
        examples: list[dict],
    ) -> dict | None:
        """Translate via Grok. Returns parsed dict or None."""
        if not self._ai_service:
            return None

        grok = getattr(self._ai_service, "_grok", None)
        if not grok or not grok.available:
            return None

        system, prompt = self._build_prompt(
            transliteration, gardiner_sequence, examples
        )

        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ]
            resp = await grok._chat_completion(
                messages,
                temperature=0.2,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            text = grok._extract_text(resp)
            if text:
                data = self._parse_json(text)
                if data and (data.get("translation_en") or data.get("translation_ar")):
                    return data
            return None
        except Exception:
            logger.warning("Grok translation failed", exc_info=True)
            return None

    # ── Public API (async) ──

    async def translate_async(
        self,
        transliteration: str,
        gardiner_sequence: str = "",
    ) -> dict:
        """Translate MdC → EN + AR with RAG + fallback chain.

        Flow: cache → RAG retrieve → Gemini → Groq → Grok → cache result
        """
        t0 = time.perf_counter()

        # 1. Cache check
        cached = self._cache.get(transliteration)
        if cached:
            cached["from_cache"] = True
            cached["latency_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            return cached

        # 2. RAG retrieval
        examples = await self.aretrieve(transliteration)

        # 3. Fallback chain: Gemini → Groq → Grok
        result = None
        provider = ""

        result = await self._translate_gemini(
            transliteration, gardiner_sequence, examples
        )
        if result:
            provider = "gemini"

        if not result:
            result = await self._translate_groq(
                transliteration, gardiner_sequence, examples
            )
            if result:
                provider = "groq"

        if not result:
            result = await self._translate_grok(
                transliteration, gardiner_sequence, examples
            )
            if result:
                provider = "grok"

        latency = round((time.perf_counter() - t0) * 1000, 1)

        example_list = [
            {
                "transliteration": e["transliteration"],
                "translation_en": e["translation_en"],
                "similarity": e.get("similarity", 0),
            }
            for e in examples
        ]

        if result:
            output = {
                "transliteration": transliteration,
                "english": result.get("translation_en", ""),
                "arabic": result.get("translation_ar", ""),
                "context": result.get("context", ""),
                "examples": example_list,
                "provider": provider,
                "latency_ms": latency,
                "from_cache": False,
                "error": None,
            }
            self._cache.put(transliteration, output)
            return output

        return {
            "transliteration": transliteration,
            "english": "",
            "arabic": "",
            "context": "",
            "examples": example_list,
            "provider": "",
            "latency_ms": latency,
            "from_cache": False,
            "error": "All translation providers failed",
        }

    # ── Sync wrappers (backward compat with pipeline._translate()) ──

    def translate_bilingual(
        self,
        transliteration: str,
        max_retries: int = 5,
        gardiner_sequence: str = "",
    ) -> dict:
        """Synchronous bilingual translate — for pipeline._translate() compat."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Inside async context — run in a separate thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self.translate_async(transliteration, gardiner_sequence),
                )
                result = future.result(timeout=30)
        else:
            result = asyncio.run(
                self.translate_async(transliteration, gardiner_sequence)
            )

        # Map to old format expected by pipeline._translate()
        return {
            "english": result.get("english", ""),
            "arabic": result.get("arabic", ""),
            "model": result.get("provider", ""),
            "latency_ms": result.get("latency_ms", 0),
            "en_error": result.get("error"),
            "ar_error": result.get("error"),
            "examples": result.get("examples", []),
        }
