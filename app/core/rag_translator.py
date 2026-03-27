"""H5.4 + H5.5: RAG retrieval pipeline + Gemini translation.

Architecture:
    1. Query transliteration -> embed
    2. FAISS search -> top-k similar corpus entries
    3. Format examples as few-shot context
    4. Send to Gemini 2.5 Flash for translation

Uses 17 rotating Gemini API keys for rate limit management.
"""

from __future__ import annotations

import json
import os
import random
import re
import time
from pathlib import Path

import numpy as np

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    faiss = None
    HAS_FAISS = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # Wadjet-v2/
EMBED_DIR = PROJECT_ROOT / "data" / "embeddings"


class GeminiKeyRotator:
    """Rotate through multiple Gemini API keys to stay under rate limits."""

    def __init__(self, keys: list[str] | None = None) -> None:
        if keys:
            self.keys = list(keys)
        else:
            # Fallback: try comma-separated GEMINI_API_KEYS
            csv = os.environ.get("GEMINI_API_KEYS", "")
            self.keys = [k.strip() for k in csv.split(",") if k.strip()]
        if not self.keys:
            # Legacy: try numbered GEMINI_API_KEY_01..29
            for i in range(1, 30):
                key = os.environ.get(f"GEMINI_API_KEY_{i:02d}", "")
                if key:
                    self.keys.append(key)
        if not self.keys:
            raise RuntimeError("No Gemini API keys found (set GEMINI_API_KEYS)")
        self._idx = 0

    def next_key(self) -> str:
        key = self.keys[self._idx % len(self.keys)]
        self._idx += 1
        return key

    @property
    def count(self) -> int:
        return len(self.keys)


class RAGTranslator:
    """RAG-based Ancient Egyptian transliteration -> English translator."""

    def __init__(
        self,
        embed_model_name: str = "all-MiniLM-L6-v2",
        gemini_model: str = "gemini-2.5-flash",
        top_k: int = 5,
        temperature: float = 0.3,
    ) -> None:
        self.top_k = top_k
        self.gemini_model = gemini_model
        self.temperature = temperature

        # Load embedding model (optional — falls back to Gemini-only if unavailable)
        self.embed_model = None
        self.index = None
        self.corpus = None

        if HAS_SENTENCE_TRANSFORMERS and HAS_FAISS:
            self.embed_model = SentenceTransformer(embed_model_name)
            index_path = EMBED_DIR / "corpus.index"
            if index_path.exists():
                self.index = faiss.read_index(str(index_path))
                if hasattr(self.index, "nprobe"):
                    self.index.nprobe = 10
                corpus_path = EMBED_DIR / "corpus_ids.json"
                with open(corpus_path, encoding="utf-8") as f:
                    self.corpus = json.load(f)

        # Key rotator
        self.key_rotator = GeminiKeyRotator()

        # Lazy import google.genai
        self._client = None

    def _get_client(self, api_key: str):
        """Get or create a Gemini client with the given API key."""
        from google import genai
        from google.genai.types import HttpOptions, HttpRetryOptions
        return genai.Client(
            api_key=api_key,
            http_options=HttpOptions(
                timeout=30_000,
                api_version="v1beta",
                # Disable internal retries — we do our own key rotation
                retry_options=HttpRetryOptions(attempts=1),
            ),
        )

    def retrieve(self, transliteration: str, top_k: int | None = None) -> list[dict]:
        """Retrieve top-k similar corpus entries for a transliteration."""
        if self.embed_model is None or self.index is None:
            return []
        k = top_k or self.top_k
        text = f"{transliteration} ||| "
        embedding = self.embed_model.encode(
            [text], normalize_embeddings=True
        ).astype("float32")

        D, I = self.index.search(embedding, k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            entry = self.corpus[idx].copy()
            entry["similarity"] = float(dist)
            results.append(entry)
        return results

    def _build_prompt(
        self,
        transliteration: str,
        examples: list[dict],
        target_lang: str = "english",
    ) -> str:
        """Build the few-shot prompt for Gemini."""
        is_arabic = target_lang.lower() in ("arabic", "ar")

        prompt_parts = [
            "You are an expert Egyptologist specializing in Ancient Egyptian "
            "language translation. Translate the following Ancient Egyptian "
            "transliteration (in Manuel de Codage notation) into modern "
            f"{target_lang}.\n",
            "RULES:",
            "- Produce a LITERAL, word-for-word translation",
            "- You MUST reuse the exact English words from the examples below",
            "- Do NOT rephrase, paraphrase, or use synonyms when an example "
            "already shows the standard translation for a word",
            "- Keep the same sentence structure and word order as the examples",
        ]

        if is_arabic:
            prompt_parts.extend([
                "- Use Modern Standard Arabic (فصحى)",
                "- Use conventional Arabic Egyptological terms where available",
                "- God names: use established Arabic forms (آمون، رع، أوزيريس، إيزيس، حورس)",
                "- Pharaoh names: use Arabic conventional forms (رمسيس، تحتمس، إخناتون)",
            ])
        else:
            prompt_parts.extend([
                "- Use conventional Egyptological English vocabulary",
                "- Proper nouns (god names, pharaoh names, place names): use "
                "EXACTLY the English form shown in the examples",
            ])

        prompt_parts.extend([
            "- Determinatives (marked with {det:...}) indicate semantic "
            "categories but are not pronounced",
            "- If uncertain, choose the translation closest to the examples\n",
        ])

        if examples:
            prompt_parts.append(
                "REFERENCE TRANSLATIONS from a scholarly corpus. You MUST "
                "copy vocabulary, phrasing, and style from these examples "
                "as closely as possible — treat them as the gold standard:\n"
            )
            for i, ex in enumerate(examples, 1):
                prompt_parts.append(
                    f"Example {i}:\n"
                    f"  Transliteration: {ex['transliteration']}\n"
                    f"  Translation: {ex['translation_en']}\n"
                )

        prompt_parts.append(
            f"\nNow translate this transliteration into {target_lang}:\n"
            f"  Transliteration: {transliteration}\n\n"
            f"Provide ONLY the translation, nothing else."
        )

        return "\n".join(prompt_parts)

    def translate(
        self,
        transliteration: str,
        target_lang: str = "english",
        max_retries: int = 3,
    ) -> dict:
        """Translate a transliteration using RAG + Gemini.

        Returns dict with keys: translation, examples, model, latency_ms
        """
        t0 = time.time()

        # Step 1: Retrieve similar examples
        examples = self.retrieve(transliteration)

        # Step 2: Build prompt
        prompt = self._build_prompt(transliteration, examples, target_lang)

        # Step 3: Call Gemini with key rotation + retries
        translation = None
        last_error = None

        for attempt in range(max_retries):
            key = self.key_rotator.next_key()
            try:
                from google.genai import types
                client = self._get_client(key)
                response = client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=self.temperature,
                        max_output_tokens=1024,
                    ),
                )
                if response.text:
                    translation = response.text.strip()
                    break
            except KeyboardInterrupt:
                raise
            except Exception as e:
                last_error = str(e)
                err_str = str(e).lower()
                if "429" in err_str or "resource_exhausted" in err_str:
                    # Rate limited — wait before trying next key
                    time.sleep(2.0)
                else:
                    time.sleep(0.5 + attempt * 0.5)

        latency = (time.time() - t0) * 1000

        if translation is None:
            return {
                "translation": f"[ERROR: {last_error}]",
                "examples": examples,
                "model": self.gemini_model,
                "latency_ms": round(latency, 1),
                "error": last_error,
            }

        return {
            "translation": translation,
            "examples": [
                {"transliteration": e["transliteration"],
                 "translation_en": e["translation_en"],
                 "similarity": e["similarity"]}
                for e in examples
            ],
            "model": self.gemini_model,
            "latency_ms": round(latency, 1),
        }

    def translate_bilingual(
        self,
        transliteration: str,
        max_retries: int = 3,
    ) -> dict:
        """Translate into both English and Arabic.

        Returns dict with keys: english, arabic, examples, latency_ms
        """
        en_result = self.translate(transliteration, "english", max_retries)
        ar_result = self.translate(transliteration, "arabic", max_retries)

        return {
            "transliteration": transliteration,
            "english": en_result.get("translation", ""),
            "arabic": ar_result.get("translation", ""),
            "examples": en_result.get("examples", []),
            "model": self.gemini_model,
            "latency_ms": en_result.get("latency_ms", 0) + ar_result.get("latency_ms", 0),
            "en_error": en_result.get("error"),
            "ar_error": ar_result.get("error"),
        }

    def translate_batch(
        self,
        transliterations: list[str],
        target_lang: str = "english",
        delay: float = 0.5,
    ) -> list[dict]:
        """Translate multiple transliterations with rate limiting."""
        results = []
        for i, t in enumerate(transliterations):
            result = self.translate(t, target_lang)
            results.append(result)
            if i < len(transliterations) - 1:
                time.sleep(delay)
        return results


def quick_test() -> None:
    """Quick functional test of the RAG pipeline."""
    print("=" * 60)
    print("H5.4+H5.5: RAG Translation Pipeline Test")
    print("=" * 60)

    translator = RAGTranslator()
    print(f"  Keys: {translator.key_rotator.count}")
    print(f"  Corpus: {len(translator.corpus)} entries")
    print(f"  Index: {translator.index.ntotal} vectors")

    test_cases = [
        "Htp-di-nsw",          # Royal offering formula
        "anx wDA snb",          # Life, prosperity, health
        "nTr aA nb pt",         # Great god, lord of heaven
        "jmAx xr wsjr",        # Revered before Osiris
        "nsw-bjtj nb tAwj",    # King of Upper and Lower Egypt
    ]

    print(f"\n  Testing {len(test_cases)} transliterations...\n")
    for translit in test_cases:
        print(f"  Input: {translit}")

        # Test retrieval only first
        examples = translator.retrieve(translit)
        print(f"  Top match: [{examples[0]['similarity']:.3f}] "
              f"{examples[0]['translation_en'][:60]}")

        # Full translation via Gemini
        result = translator.translate(translit)
        print(f"  Translation: {result['translation'][:80]}")
        print(f"  Latency: {result['latency_ms']:.0f}ms")
        if "error" in result:
            print(f"  ERROR: {result['error']}")
        print()

    print("Done!")


if __name__ == "__main__":
    quick_test()
