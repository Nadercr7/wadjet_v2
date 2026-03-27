"""H-TRANSLATE-02: Rebuild FAISS index with Gemini gemini-embedding-001 (768-dim).

Reads 15,604 entries from data/translation/corpus.jsonl, embeds all via
Gemini text-embedding-004, builds FAISS IndexFlatIP, saves to data/embeddings/.

Usage:
    python scripts/build_translation_index.py              # Full rebuild
    python scripts/build_translation_index.py --dry-run    # Count entries only
    python scripts/build_translation_index.py --batch 50   # Custom batch size
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CORPUS_PATH = PROJECT_ROOT / "data" / "translation" / "corpus.jsonl"
EMBED_DIR = PROJECT_ROOT / "data" / "embeddings"

# Gemini embedding config
EMBED_MODEL = "gemini-embedding-001"
DIMENSION = 768
MAX_BATCH = 100  # Gemini API limit


def load_corpus(path: Path) -> list[dict]:
    """Load corpus.jsonl entries."""
    entries = []
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                print(f"  WARNING: Skipping malformed line {i}")
    return entries


def get_gemini_keys() -> list[str]:
    """Get all Gemini API keys from environment."""
    keys_csv = os.environ.get("GEMINI_API_KEYS", "")
    keys = [k.strip() for k in keys_csv.split(",") if k.strip()]
    if not keys:
        raise RuntimeError("No GEMINI_API_KEYS found in environment")
    print(f"  Found {len(keys)} Gemini API key(s)")
    return keys


def make_client(api_key: str):
    """Create a Gemini client with the given API key."""
    from google import genai
    from google.genai.types import HttpOptions

    return genai.Client(
        api_key=api_key,
        http_options=HttpOptions(timeout=60_000, api_version="v1beta"),
    )


def embed_batch(client, texts: list[str]) -> np.ndarray:
    """Embed a batch of texts. Returns (N, 768) float32 array."""
    from google.genai.types import EmbedContentConfig

    result = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=EmbedContentConfig(output_dimensionality=DIMENSION),
    )
    arr = np.array([e.values for e in result.embeddings], dtype=np.float32)
    # L2 normalize for cosine similarity via IndexFlatIP
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    return arr / norms


def main():
    parser = argparse.ArgumentParser(description="Rebuild translation FAISS index")
    parser.add_argument("--dry-run", action="store_true", help="Count entries only")
    parser.add_argument("--batch", type=int, default=MAX_BATCH, help="Batch size (max 100)")
    args = parser.parse_args()

    print("=" * 60)
    print("H-TRANSLATE-02: Rebuild FAISS Index (gemini-embedding-001 @768-dim)")
    print("=" * 60)

    # Load corpus
    print(f"\n  Loading corpus from {CORPUS_PATH}")
    entries = load_corpus(CORPUS_PATH)
    print(f"  Loaded {len(entries)} entries")

    if args.dry_run:
        print("\n  DRY RUN — no embedding or index creation")
        sources = {}
        for e in entries:
            s = e.get("source", "unknown")
            sources[s] = sources.get(s, 0) + 1
        print(f"\n  Sources:")
        for s, c in sorted(sources.items(), key=lambda x: -x[1]):
            print(f"    {s}: {c}")
        return

    # Validate batch size
    batch_size = min(args.batch, MAX_BATCH)

    # Create clients for all keys (rotate to avoid rate limits)
    print(f"\n  Creating Gemini clients...")
    keys = get_gemini_keys()
    clients = [make_client(k) for k in keys]
    num_keys = len(clients)

    # Prepare texts for embedding
    texts = [e["transliteration"] for e in entries]
    total = len(texts)
    num_batches = (total + batch_size - 1) // batch_size

    print(f"\n  Embedding {total} texts in {num_batches} batches of {batch_size}...")
    print(f"  Model: {EMBED_MODEL} ({DIMENSION}-dim)")
    print(f"  Key rotation: {num_keys} keys (throttled ~{num_keys} RPM)")

    all_embeddings = []
    t0 = time.time()
    failed_batches = 0
    key_idx = 0
    consecutive_fails = 0

    for i in range(0, total, batch_size):
        batch_num = i // batch_size + 1
        batch_texts = texts[i : i + batch_size]

        # Rotate through keys each batch
        success = False

        for attempt in range(min(num_keys, 5)):
            client = clients[key_idx % num_keys]
            key_idx += 1
            try:
                embs = embed_batch(client, batch_texts)
                all_embeddings.append(embs)
                success = True
                consecutive_fails = 0
                break
            except Exception as e:
                err = str(e).lower()
                if "429" in err or "resource_exhausted" in err:
                    if attempt < min(num_keys, 5) - 1:
                        time.sleep(2)
                    continue
                else:
                    print(f"    ERROR batch {batch_num}: {str(e)[:100]}")
                    break

        if not success:
            consecutive_fails += 1
            failed_batches += 1
            zeros = np.zeros((len(batch_texts), DIMENSION), dtype=np.float32)
            all_embeddings.append(zeros)

            if consecutive_fails >= 5:
                # All keys exhausted — wait for quota reset
                print(f"    All keys rate-limited at batch {batch_num}. Waiting 60s...")
                time.sleep(60)
                consecutive_fails = 0

        if batch_num % 10 == 0 or batch_num == num_batches:
            elapsed = time.time() - t0
            done = i + len(batch_texts)
            rate = done / elapsed if elapsed > 0 else 0
            print(
                f"    Batch {batch_num}/{num_batches} — "
                f"{done}/{total} texts — "
                f"{rate:.0f} texts/sec — "
                f"{failed_batches} failed"
            )

        # Throttle: spread requests across keys (~1 req per key per 4s = 15 RPM effective)
        if batch_num < num_batches:
            time.sleep(max(0.5, 60.0 / num_keys))

    elapsed = time.time() - t0
    embeddings = np.vstack(all_embeddings)
    print(f"\n  Embedding complete: {embeddings.shape} in {elapsed:.1f}s")
    if failed_batches > 0:
        print(f"  WARNING: {failed_batches} batches failed (filled with zeros)")

    # Build FAISS index
    import faiss

    print(f"\n  Building FAISS IndexFlatIP ({DIMENSION}-dim)...")
    index = faiss.IndexFlatIP(DIMENSION)
    index.add(embeddings)
    print(f"  Index contains {index.ntotal} vectors")

    # Save
    EMBED_DIR.mkdir(parents=True, exist_ok=True)

    # Backup old index if exists
    old_index = EMBED_DIR / "corpus.index"
    if old_index.exists():
        backup = EMBED_DIR / "corpus.index.bak"
        import shutil
        shutil.copy2(old_index, backup)
        print(f"  Backed up old index to {backup.name}")

    old_ids = EMBED_DIR / "corpus_ids.json"
    if old_ids.exists():
        backup = EMBED_DIR / "corpus_ids.json.bak"
        import shutil
        shutil.copy2(old_ids, backup)
        print(f"  Backed up old corpus_ids to {backup.name}")

    # Write new index
    index_path = EMBED_DIR / "corpus.index"
    faiss.write_index(index, str(index_path))
    print(f"  Saved index: {index_path} ({index_path.stat().st_size / 1024 / 1024:.1f} MB)")

    # Write corpus IDs
    ids_path = EMBED_DIR / "corpus_ids.json"
    corpus_ids = [
        {
            "idx": i,
            "transliteration": e["transliteration"],
            "translation_en": e["translation_en"],
            "source": e.get("source", "unknown"),
        }
        for i, e in enumerate(entries)
    ]
    with open(ids_path, "w", encoding="utf-8") as f:
        json.dump(corpus_ids, f, ensure_ascii=False)
    print(f"  Saved corpus IDs: {ids_path} ({ids_path.stat().st_size / 1024:.0f} KB)")

    # Write stats
    stats = {
        "model": EMBED_MODEL,
        "dimension": DIMENSION,
        "num_vectors": int(index.ntotal),
        "num_corpus_entries": len(entries),
        "index_type": "IndexFlatIP",
        "normalized": True,
        "failed_batches": failed_batches,
        "build_time_seconds": round(elapsed, 1),
    }
    stats_path = EMBED_DIR / "embed_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"  Saved stats: {stats_path}")

    # Quick sanity check
    print(f"\n  Sanity check — searching for 'Htp-di-nsw'...")
    q = embed_batch(clients[0], ["Htp-di-nsw"])
    D, I = index.search(q, 5)
    for dist, idx in zip(D[0], I[0]):
        if 0 <= idx < len(corpus_ids):
            e = corpus_ids[idx]
            print(f"    [{dist:.3f}] {e['transliteration']} → {e['translation_en'][:60]}")

    print(f"\n  Done! Index rebuilt with {index.ntotal} vectors ({DIMENSION}-dim)")


if __name__ == "__main__":
    main()
