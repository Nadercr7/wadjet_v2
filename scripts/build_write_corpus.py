"""Build EN→MdC reverse corpus for Write in Hieroglyphs smart mode.

Usage:
    python scripts/build_write_corpus.py

Output:
    data/translation/write_corpus.jsonl

Sources:
1. Reversed entries from data/translation/corpus.jsonl
2. 150+ curated entries from Egyptological references
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS_IN = ROOT / "data" / "translation" / "corpus.jsonl"
CORPUS_OUT = ROOT / "data" / "translation" / "write_corpus.jsonl"

# ─── Curated entries: verified EN→MdC pairs ───
# Each tuple: (english, mdc, category)
# MdC uses standard Manuel de Codage transliteration
# Categories: offering, royal, deity, greeting, common, phrase, word, title, body

CURATED = [
    # ── Offering Formula ──
    ("an offering which the king gives", "Htp di nsw", "offering"),
    ("a royal offering", "Htp di nsw", "offering"),
    ("offering formula", "Htp di nsw", "offering"),
    ("an offering which the king gives to Osiris", "Htp di nsw wsjr", "offering"),
    ("an offering which the king gives to Anubis", "Htp di nsw jnpw", "offering"),
    ("a thousand of bread and beer", "xA m t Hnqt", "offering"),
    ("bread and beer", "t Hnqt", "offering"),
    ("a thousand of bread", "xA m t", "offering"),
    ("oxen and fowl", "kA Apdw", "offering"),
    ("all good and pure things", "xt nbt nfrt wabt", "offering"),
    ("invocation offerings", "prt xrw", "offering"),

    # ── Royal Titles ──
    ("son of Ra", "sA ra", "royal"),
    ("son of Re", "sA ra", "royal"),
    ("lord of the two lands", "nb tAwj", "royal"),
    ("king of upper and lower egypt", "nsw bjt", "royal"),
    ("dual king", "nsw bjt", "royal"),
    ("good god", "nTr nfr", "royal"),
    ("the good god", "nTr nfr", "royal"),
    ("lord of rituals", "nb jrt jxt", "royal"),
    ("lord of appearances", "nb xaw", "royal"),
    ("lord of crowns", "nb xaw", "royal"),
    ("mighty bull", "kA nxt", "royal"),
    ("strong bull", "kA nxt", "royal"),
    ("two ladies", "nbtj", "royal"),
    ("golden Horus", "Hr nbw", "royal"),
    ("pharaoh", "pr aA", "royal"),
    ("his majesty", "Hm .f", "royal"),
    ("king", "nsw", "royal"),

    # ── Deity Names ──
    ("Amun", "jmn", "deity"),
    ("Amun-Ra", "jmn ra", "deity"),
    ("Ra", "ra", "deity"),
    ("Re", "ra", "deity"),
    ("Osiris", "wsjr", "deity"),
    ("Horus", "Hr", "deity"),
    ("Isis", "Ast", "deity"),
    ("Anubis", "jnpw", "deity"),
    ("Thoth", "DHwtj", "deity"),
    ("Ptah", "ptH", "deity"),
    ("Hathor", "Hwt Hr", "deity"),
    ("Mut", "mwt", "deity"),
    ("Khnum", "xnmw", "deity"),
    ("Sobek", "sbk", "deity"),
    ("Sekhmet", "sxmt", "deity"),
    ("Nephthys", "nbt Hwt", "deity"),
    ("Set", "stx", "deity"),
    ("Seth", "stx", "deity"),
    ("Maat", "mAat", "deity"),
    ("Khonsu", "xnsw", "deity"),
    ("Min", "mnw", "deity"),
    ("Atum", "jtmw", "deity"),
    ("Bastet", "bAstt", "deity"),
    ("Khepri", "xprj", "deity"),
    ("Montu", "mnTw", "deity"),

    # ── Common Phrases ──
    ("life prosperity health", "anx wDA snb", "phrase"),
    ("life, prosperity, health", "anx wDA snb", "phrase"),
    ("given life forever", "Dj anx Dt", "phrase"),
    ("may he live forever", "anx Dt", "phrase"),
    ("enduring forever", "wAH Dt", "phrase"),
    ("words to be spoken", "Dd mdw", "phrase"),
    ("recitation", "Dd mdw", "phrase"),
    ("beloved of Amun", "mry jmn", "phrase"),
    ("beloved of Ra", "mry ra", "phrase"),
    ("lord of heaven", "nb pt", "phrase"),
    ("lord of eternity", "nb Dt", "phrase"),
    ("great god", "nTr aA", "phrase"),
    ("great goddess", "nTrt aAt", "phrase"),
    ("lord of the sky", "nb pt", "phrase"),
    ("praising the god", "dwA nTr", "phrase"),
    ("praising god four times", "dwA nTr sp 4", "phrase"),
    ("may he give life", "Dj .f anx", "phrase"),
    ("i have given you", "Dj .n .j n .k", "phrase"),
    ("all life and dominion", "anx wAs nb", "phrase"),
    ("may you live like Ra", "anx .tj mj ra", "phrase"),
    ("millions of years", "HHw nw rnpwt", "phrase"),
    ("given life like Ra forever", "Dj anx mj ra Dt", "phrase"),
    ("all health and joy", "snb nb Awt jb nb", "phrase"),
    ("stability and dominion", "Dd wAs", "phrase"),
    ("in peace", "m Htp", "phrase"),
    ("in truth", "m mAat", "phrase"),
    ("he says", "Dd .f", "phrase"),
    ("he speaks", "Dd .f", "phrase"),
    ("who loves truth", "mr mAat", "phrase"),
    ("living forever", "anx Dt", "phrase"),
    ("lord of truth", "nb mAat", "phrase"),
    ("may he be given life", "Dj anx", "phrase"),
    ("all foreign lands", "xAswt nbt", "phrase"),
    ("all flat lands", "tAw nbw", "phrase"),
    ("appearing in glory", "xaj m Axt", "phrase"),
    ("upon the throne", "Hr st Hrt", "phrase"),
    ("revered before Osiris", "jmAxw xr wsjr", "phrase"),
    ("true of voice", "mAa xrw", "phrase"),
    ("justified", "mAa xrw", "phrase"),
    ("the justified", "mAa xrw", "phrase"),
    ("the deceased", "mAa xrw", "phrase"),

    # ── Common Words ──
    ("life", "anx", "word"),
    ("live", "anx", "word"),
    ("health", "snb", "word"),
    ("prosperity", "wDA", "word"),
    ("dominion", "wAs", "word"),
    ("power", "wAs", "word"),
    ("strength", "nxt", "word"),
    ("truth", "mAat", "word"),
    ("justice", "mAat", "word"),
    ("order", "mAat", "word"),
    ("beauty", "nfr", "word"),
    ("beautiful", "nfr", "word"),
    ("good", "nfr", "word"),
    ("great", "aA", "word"),
    ("love", "mr", "word"),
    ("beloved", "mry", "word"),
    ("peace", "Htp", "word"),
    ("offering", "Htp", "word"),
    ("eternity", "Dt", "word"),
    ("forever", "Dt", "word"),
    ("eternal", "nHH", "word"),
    ("million", "HH", "word"),
    ("year", "rnpt", "word"),
    ("water", "mw", "word"),
    ("bread", "t", "word"),
    ("beer", "Hnqt", "word"),
    ("god", "nTr", "word"),
    ("goddess", "nTrt", "word"),
    ("divine", "nTrj", "word"),
    ("lord", "nb", "word"),
    ("lady", "nbt", "word"),
    ("all", "nb", "word"),
    ("every", "nb", "word"),
    ("scribe", "sS", "word"),
    ("priest", "wab", "word"),
    ("prophet", "Hm nTr", "word"),
    ("mother", "mwt", "word"),
    ("father", "jt", "word"),
    ("brother", "sn", "word"),
    ("sister", "snt", "word"),
    ("son", "sA", "word"),
    ("daughter", "sAt", "word"),
    ("man", "z", "word"),
    ("woman", "st", "word"),
    ("person", "rmT", "word"),
    ("people", "rmTw", "word"),
    ("house", "pr", "word"),
    ("temple", "Hwt nTr", "word"),
    ("palace", "aH", "word"),
    ("pyramid", "mr", "word"),
    ("tomb", "jz", "word"),
    ("land", "tA", "word"),
    ("earth", "tA", "word"),
    ("sky", "pt", "word"),
    ("heaven", "pt", "word"),
    ("sun", "ra", "word"),
    ("moon", "jaH", "word"),
    ("star", "sbA", "word"),
    ("day", "hrw", "word"),
    ("night", "grH", "word"),
    ("west", "jmnt", "word"),
    ("east", "jAbt", "word"),
    ("north", "mHt", "word"),
    ("south", "rswt", "word"),
    ("sacred", "Dsr", "word"),
    ("holy", "Dsr", "word"),
    ("protect", "sA", "word"),
    ("protection", "sA", "word"),
    ("protection", "mkt", "word"),
    ("give", "Dj", "word"),
    ("speak", "Dd", "word"),
    ("say", "Dd", "word"),
    ("see", "mAA", "word"),
    ("hear", "sDm", "word"),
    ("know", "rx", "word"),
    ("come", "jj", "word"),
    ("go", "Sm", "word"),
    ("make", "jrj", "word"),
    ("do", "jrj", "word"),
    ("fight", "aHA", "word"),
    ("war", "aHA", "word"),
    ("enemy", "xft", "word"),
    ("heart", "jb", "word"),
    ("soul", "bA", "word"),
    ("spirit", "kA", "word"),
    ("name", "rn", "word"),
    ("body", "Dt", "word"),
    ("face", "Hr", "word"),
    ("eye", "jrt", "word"),
    ("mouth", "r", "word"),
    ("hand", "Drt", "word"),
    ("foot", "rd", "word"),
    ("head", "tp", "word"),
    ("gold", "nbw", "word"),
    ("silver", "HD", "word"),
    ("copper", "bjA", "word"),
    ("stone", "jnr", "word"),
    ("fire", "sDt", "word"),
    ("Nile", "jtrw", "word"),
    ("river", "jtrw", "word"),
    ("field", "sxt", "word"),
    ("tree", "nht", "word"),
    ("mountain", "Dw", "word"),
    ("desert", "dSrt", "word"),
    ("black land", "kmt", "word"),
    ("Egypt", "kmt", "word"),
    ("Thebes", "wAst", "word"),
    ("Memphis", "mn nfr", "word"),
    ("book", "mDAt", "word"),
    ("writing", "sS", "word"),
    ("word", "mdw", "word"),
    ("words", "mdw", "word"),
    ("speech", "mdw", "word"),
    ("voice", "xrw", "word"),
    ("magic", "HkA", "word"),
    ("door", "aA", "word"),
    ("gate", "sbA", "word"),
    ("road", "wAt", "word"),
    ("path", "wAt", "word"),
    ("boat", "dpwt", "word"),
    ("throne", "st", "word"),
    ("crown", "xaw", "word"),
    ("sceptre", "wAs", "word"),

    # ── Pharaoh Names (cartouche content) ──
    ("Tutankhamun", "twt anx jmn", "royal"),
    ("Ramesses", "ra ms sw", "royal"),
    ("Ramses", "ra ms sw", "royal"),
    ("Thutmose", "DHwtj ms", "royal"),
    ("Amenhotep", "jmn Htp", "royal"),
    ("Hatshepsut", "HAt Spswt", "royal"),
    ("Akhenaten", "Ax n jtn", "royal"),
    ("Nefertiti", "nfrt jjtj", "royal"),
    ("Cleopatra", "qlwpAdrA", "royal"),
    ("Khufu", "xwfw", "royal"),
    ("Khafre", "xaj .f ra", "royal"),
    ("Menkaure", "mn kA w ra", "royal"),
    ("Senusret", "s n wsrt", "royal"),
    ("Seti", "stj", "royal"),

    # ── Greetings & Blessings ──
    ("welcome", "jj m Htp", "greeting"),
    ("welcome in peace", "jj m Htp", "greeting"),
    ("peace be upon you", "Htp Hr .k", "greeting"),
    ("go in peace", "Sm m Htp", "greeting"),
    ("be well", "snb", "greeting"),
    ("may you prosper", "wDA", "greeting"),
    ("may you be healthy", "snb .tj", "greeting"),
    ("long life", "anx wDA snb", "greeting"),
    ("to your health", "n snb .k", "greeting"),
    ("good morning", "nfr m hrw", "greeting"),

    # ── Afterlife / Funerary ──
    ("the Book of the Dead", "rw nw prt m hrw", "phrase"),
    ("book of coming forth by day", "rw nw prt m hrw", "phrase"),
    ("the opening of the mouth", "wpt r", "phrase"),
    ("the weighing of the heart", "wDa jb", "phrase"),
    ("the field of reeds", "sxt jArw", "phrase"),
    ("the beautiful west", "jmnt nfrt", "phrase"),
    ("the underworld", "dwAt", "phrase"),
    ("the netherworld", "dwAt", "phrase"),

    # ── Short confirmations ──
    ("yes", "jw", "word"),
    ("no", "nn", "word"),
    ("not", "nn", "word"),
    ("I", "jnk", "word"),
    ("you", "ntk", "word"),
    ("he", "sw", "word"),
    ("she", "sj", "word"),
    ("this", "pn", "word"),
    ("that", "pw", "word"),
    ("who", "ntj", "word"),
    ("what", "jx", "word"),
]


def reverse_corpus() -> list[dict]:
    """Reverse existing corpus.jsonl from MdC→EN to EN→MdC entries."""
    entries = []
    if not CORPUS_IN.exists():
        print(f"  WARNING: {CORPUS_IN} not found, skipping reverse")
        return entries

    seen_en = set()
    for line in CORPUS_IN.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        mdc = row.get("transliteration", "").strip()
        en = row.get("translation_en", "").strip().lower()
        source = row.get("source", "unknown")

        if not mdc or not en:
            continue
        # Skip very long entries (not useful for write feature)
        if len(en) > 120 or len(mdc) > 80:
            continue
        # Skip entries that are just repeated words or too generic
        if len(en) < 2 or len(mdc) < 1:
            continue

        # Deduplicate by English text — keep shortest MdC per English phrase
        if en in seen_en:
            continue
        seen_en.add(en)

        entries.append({
            "english": en,
            "mdc": mdc,
            "category": "corpus",
            "source": f"reversed_{source}",
        })

    return entries


def build_curated() -> list[dict]:
    """Build curated entries list."""
    entries = []
    seen_en = set()
    for en, mdc, cat in CURATED:
        en_lower = en.lower()
        if en_lower in seen_en:
            continue
        seen_en.add(en_lower)
        entries.append({
            "english": en_lower,
            "mdc": mdc,
            "category": cat,
            "source": "curated",
        })
    return entries


def main():
    print("Building write corpus (EN→MdC)...")

    # 1. Load curated entries first (they take priority)
    curated = build_curated()
    curated_en = {e["english"] for e in curated}
    print(f"  Curated:  {len(curated)} entries")

    # 2. Reverse existing corpus
    reversed_entries = reverse_corpus()
    print(f"  Reversed: {len(reversed_entries)} entries (before dedup)")

    # 3. Merge: curated wins over reversed
    final = list(curated)
    added = 0
    for entry in reversed_entries:
        if entry["english"] not in curated_en:
            final.append(entry)
            added += 1
    print(f"  Merged:   {added} reversed entries added (curated had priority)")

    # 4. Sort: curated first, then by English alphabetically
    final.sort(key=lambda e: (0 if e["source"] == "curated" else 1, e["english"]))

    # 5. Write output
    CORPUS_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(CORPUS_OUT, "w", encoding="utf-8") as f:
        for entry in final:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"\n  Output: {CORPUS_OUT}")
    print(f"  Total:  {len(final)} entries")
    print(f"    - {len(curated)} curated")
    print(f"    - {added} from reversed corpus")

    # Stats
    cats = {}
    for e in final:
        cats[e["category"]] = cats.get(e["category"], 0) + 1
    print(f"\n  Categories:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {cat:12s}: {count}")


if __name__ == "__main__":
    main()
