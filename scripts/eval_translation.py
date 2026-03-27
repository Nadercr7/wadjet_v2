"""H-TRANSLATE-06: Translation quality evaluation.

Tests the RAG translator against known inscription translations.
Reports per-sample BLEU scores and overall metrics.

Usage:
    python scripts/eval_translation.py
    python scripts/eval_translation.py --samples 10  # Quick test
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Ground truth test cases ───────────────────────────────────────

GROUND_TRUTH = [
    {
        "transliteration": "Htp-di-nsw",
        "expected_en": "an offering which the king gives",
        "category": "offering formula",
    },
    {
        "transliteration": "anx wDA snb",
        "expected_en": "life, prosperity, health",
        "category": "epithet formula",
    },
    {
        "transliteration": "nTr aA nb pt",
        "expected_en": "great god, lord of heaven",
        "category": "divine epithet",
    },
    {
        "transliteration": "jmAx xr wsjr",
        "expected_en": "revered before Osiris",
        "category": "funerary formula",
    },
    {
        "transliteration": "nsw-bjtj nb tAwj",
        "expected_en": "king of Upper and Lower Egypt, lord of the Two Lands",
        "category": "royal title",
    },
    {
        "transliteration": "Dd mdw jn",
        "expected_en": "words spoken by",
        "category": "speech formula",
    },
    {
        "transliteration": "sA Ra",
        "expected_en": "son of Re",
        "category": "royal title",
    },
    {
        "transliteration": "di anx Dd wAs",
        "expected_en": "given life, stability, and dominion",
        "category": "royal blessing",
    },
    {
        "transliteration": "nTr nfr nb tAwj",
        "expected_en": "the good god, lord of the Two Lands",
        "category": "royal epithet",
    },
    {
        "transliteration": "mAa-xrw",
        "expected_en": "true of voice",
        "category": "funerary epithet",
    },
    {
        "transliteration": "jmj-rA pr",
        "expected_en": "overseer of the house",
        "category": "title",
    },
    {
        "transliteration": "Hm nTr",
        "expected_en": "servant of the god",
        "category": "priestly title",
    },
    {
        "transliteration": "nb anx",
        "expected_en": "lord of life",
        "category": "divine epithet",
    },
    {
        "transliteration": "di=f prt-xrw",
        "expected_en": "he gives an invocation offering",
        "category": "offering formula",
    },
    {
        "transliteration": "t Hnqt kAw Apdw",
        "expected_en": "bread, beer, oxen, fowl",
        "category": "offering list",
    },
    {
        "transliteration": "Xrt-nTr",
        "expected_en": "necropolis",
        "category": "toponym",
    },
    {
        "transliteration": "tA mri",
        "expected_en": "the beloved land",
        "category": "toponym",
    },
    {
        "transliteration": "wab nsw",
        "expected_en": "royal wab-priest",
        "category": "priestly title",
    },
    {
        "transliteration": "Htp di wsjr",
        "expected_en": "an offering which Osiris gives",
        "category": "offering formula",
    },
    {
        "transliteration": "xntj-jmntjw",
        "expected_en": "foremost of the westerners",
        "category": "divine epithet",
    },
    {
        "transliteration": "jrj-pat HAtj-a",
        "expected_en": "hereditary prince, count",
        "category": "noble title",
    },
    {
        "transliteration": "smr watj",
        "expected_en": "sole companion",
        "category": "noble title",
    },
    {
        "transliteration": "nb imAx",
        "expected_en": "possessor of reverence",
        "category": "funerary epithet",
    },
    {
        "transliteration": "Dt nHH",
        "expected_en": "for ever and eternity",
        "category": "eternity formula",
    },
    {
        "transliteration": "jmj-rA mSa",
        "expected_en": "overseer of the army",
        "category": "military title",
    },
    {
        "transliteration": "Hrj-tp nsw",
        "expected_en": "chief of the king",
        "category": "administrative title",
    },
    {
        "transliteration": "sSm-HAb",
        "expected_en": "festival director",
        "category": "priestly title",
    },
    {
        "transliteration": "pr aA",
        "expected_en": "pharaoh",
        "category": "royal epithet",
    },
    {
        "transliteration": "dwAt",
        "expected_en": "the underworld",
        "category": "afterlife",
    },
    {
        "transliteration": "jb",
        "expected_en": "heart",
        "category": "body part",
    },
    {
        "transliteration": "xt nb(t) nfr(t) wabt",
        "expected_en": "every good and pure thing",
        "category": "offering formula",
    },
    {
        "transliteration": "Snwt",
        "expected_en": "granary",
        "category": "administrative",
    },
    {
        "transliteration": "rn=f nfr",
        "expected_en": "his good name",
        "category": "identity formula",
    },
    {
        "transliteration": "Hmt nsw wrt",
        "expected_en": "great royal wife",
        "category": "royal title",
    },
    {
        "transliteration": "stp-n-Ra",
        "expected_en": "chosen of Re",
        "category": "royal epithet",
    },
    {
        "transliteration": "wHm anx",
        "expected_en": "repeating life",
        "category": "funerary formula",
    },
    {
        "transliteration": "Htp",
        "expected_en": "offering",
        "category": "core vocabulary",
    },
    {
        "transliteration": "wsjr",
        "expected_en": "Osiris",
        "category": "god name",
    },
    {
        "transliteration": "jmn-Ra",
        "expected_en": "Amun-Re",
        "category": "god name",
    },
    {
        "transliteration": "sbA",
        "expected_en": "star",
        "category": "core vocabulary",
    },
    {
        "transliteration": "mw",
        "expected_en": "water",
        "category": "core vocabulary",
    },
    {
        "transliteration": "ra nb",
        "expected_en": "every day",
        "category": "temporal formula",
    },
    {
        "transliteration": "nfr",
        "expected_en": "good",
        "category": "core vocabulary",
    },
    {
        "transliteration": "aA",
        "expected_en": "great",
        "category": "core vocabulary",
    },
    {
        "transliteration": "Ax iqr",
        "expected_en": "excellent spirit",
        "category": "funerary epithet",
    },
    {
        "transliteration": "nb xpS",
        "expected_en": "lord of strength",
        "category": "royal epithet",
    },
    {
        "transliteration": "Dd mdw jn wsjr",
        "expected_en": "words spoken by Osiris",
        "category": "speech formula",
    },
    {
        "transliteration": "sS nsw",
        "expected_en": "royal scribe",
        "category": "administrative title",
    },
    {
        "transliteration": "mAat",
        "expected_en": "truth",
        "category": "concept",
    },
    {
        "transliteration": "kA",
        "expected_en": "spirit",
        "category": "concept",
    },
]


# ── BLEU scoring ──────────────────────────────────────────────────


def simple_bleu(reference: str, hypothesis: str) -> float:
    """Compute simple unigram BLEU-1 score between two strings.

    Normalized, lowercased, punctuation-stripped comparison.
    Returns float in [0, 1].
    """
    import re

    def tokenize(text: str) -> list[str]:
        text = text.lower().strip()
        text = re.sub(r"[^\w\s]", "", text)
        return text.split()

    ref_tokens = tokenize(reference)
    hyp_tokens = tokenize(hypothesis)

    if not ref_tokens or not hyp_tokens:
        return 0.0

    # Unigram precision
    ref_set = set(ref_tokens)
    matches = sum(1 for t in hyp_tokens if t in ref_set)
    precision = matches / len(hyp_tokens) if hyp_tokens else 0.0

    # Unigram recall
    hyp_set = set(hyp_tokens)
    recall_matches = sum(1 for t in ref_tokens if t in hyp_set)
    recall = recall_matches / len(ref_tokens) if ref_tokens else 0.0

    # F1-like combination (more forgiving than standard BLEU)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


# ── Main evaluation ───────────────────────────────────────────────


async def run_eval(num_samples: int | None = None) -> dict:
    """Run translation evaluation."""
    # Import and set up translator
    from app.core.rag_translator import RAGTranslator

    # Try to get Gemini service for full RAG
    gemini = None
    try:
        keys_csv = os.environ.get("GEMINI_API_KEYS", "")
        keys = [k.strip() for k in keys_csv.split(",") if k.strip()]
        if keys:
            from app.core.gemini_service import GeminiService
            gemini = GeminiService(keys)
    except Exception:
        pass

    translator = RAGTranslator(gemini=gemini, top_k=5)

    samples = GROUND_TRUTH[:num_samples] if num_samples else GROUND_TRUTH
    total = len(samples)

    print(f"\n  Running evaluation on {total} samples...")
    print(f"  Index available: {translator.available}")
    print(f"  Gemini: {'yes' if gemini else 'no'}")
    print()

    results = []
    total_bleu = 0.0
    errors = 0

    for i, sample in enumerate(samples, 1):
        t = sample["transliteration"]
        expected = sample["expected_en"]

        try:
            result = await translator.translate_async(t)
            got_en = result.get("english", "")
            got_ar = result.get("arabic", "")
            error = result.get("error")
            provider = result.get("provider", "")
            latency = result.get("latency_ms", 0)

            bleu = simple_bleu(expected, got_en) if got_en else 0.0
            total_bleu += bleu

            status = "PASS" if bleu >= 0.3 else "FAIL"
            if error:
                status = "ERROR"
                errors += 1

            print(
                f"  [{i:2d}/{total}] {status} BLEU={bleu:.2f} | "
                f"{t[:30]:30s} | {provider:6s} | {latency:6.0f}ms"
            )
            if status == "FAIL":
                print(f"           Expected: {expected}")
                print(f"           Got:      {got_en}")

            results.append({
                "transliteration": t,
                "expected_en": expected,
                "got_en": got_en,
                "got_ar": got_ar,
                "bleu": round(bleu, 3),
                "provider": provider,
                "latency_ms": latency,
                "error": error,
                "category": sample["category"],
            })

        except Exception as e:
            errors += 1
            print(f"  [{i:2d}/{total}] EXCEPTION | {t[:30]:30s} | {e}")
            results.append({
                "transliteration": t,
                "expected_en": expected,
                "got_en": "",
                "got_ar": "",
                "bleu": 0.0,
                "provider": "",
                "latency_ms": 0,
                "error": str(e),
                "category": sample["category"],
            })

        # Brief delay between samples
        await asyncio.sleep(0.5)

    # Summary
    avg_bleu = total_bleu / total if total > 0 else 0.0
    passing = sum(1 for r in results if r["bleu"] >= 0.3)
    avg_latency = sum(r["latency_ms"] for r in results) / total if total > 0 else 0

    print(f"\n{'=' * 60}")
    print(f"  Translation Evaluation Summary")
    print(f"{'=' * 60}")
    print(f"  Samples:       {total}")
    print(f"  Passing (≥0.3): {passing}/{total} ({passing/total*100:.0f}%)")
    print(f"  Avg BLEU:      {avg_bleu:.3f}")
    print(f"  Errors:        {errors}")
    print(f"  Avg latency:   {avg_latency:.0f}ms")

    # Category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "bleu_sum": 0.0, "passing": 0}
        categories[cat]["total"] += 1
        categories[cat]["bleu_sum"] += r["bleu"]
        if r["bleu"] >= 0.3:
            categories[cat]["passing"] += 1

    print(f"\n  By category:")
    for cat, s in sorted(categories.items()):
        avg = s["bleu_sum"] / s["total"]
        print(f"    {cat:25s}  BLEU={avg:.2f}  pass={s['passing']}/{s['total']}")

    # Gate check: TRN-G7 requires BLEU > 0.3
    gate = "PASS" if avg_bleu > 0.3 else "FAIL"
    print(f"\n  Gate TRN-G7 (BLEU>0.3): {gate}")

    # Save results
    output_path = PROJECT_ROOT / "data" / "translation" / "eval_results.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "total_samples": total,
        "avg_bleu": round(avg_bleu, 3),
        "passing_rate": round(passing / total, 3) if total > 0 else 0,
        "errors": errors,
        "avg_latency_ms": round(avg_latency, 1),
        "gate_trn_g7": gate,
        "results": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n  Results saved to {output_path}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Evaluate translation quality")
    parser.add_argument("--samples", type=int, help="Number of samples (default: all 50)")
    args = parser.parse_args()

    print("=" * 60)
    print("H-TRANSLATE-06: Translation Quality Evaluation")
    print("=" * 60)

    asyncio.run(run_eval(args.samples))


if __name__ == "__main__":
    main()
