"""
Wadjet AI - Class Similarity Service (Phase 7.4).

Computes semantic similarity between all 52 ML landmark classes using
Gemini text embeddings.  When a landmark is identified the service
returns "This also looks like ..." suggestions that are semantically
close but may not appear in the model's top-5 predictions.

Architecture
~~~~~~~~~~~~
* On first call, **lazy-initialises** embeddings for all 52 classes by
  embedding short descriptor strings (display name + category hints).
* Class categories and hints are defined locally — no dependency on the
  20 curated ``Attraction`` records (which only cover a subset).
* Cosine similarity (pure-Python, no numpy) ranks classes.
* Results are cached in-memory so subsequent calls are instant.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from app.core.cache import embedding_cache

if TYPE_CHECKING:
    from app.core.gemini_service import GeminiService

logger = structlog.get_logger("wadjet.similarity")

# ── Class metadata (all 52 classes) ──────────────────────────────────────
# Maps class_name -> (display_name, category, short hint for embedding)
# Categories: pharaonic, islamic, greco-roman, modern, natural, artifact
_CLASS_META: dict[str, tuple[str, str, str]] = {
    "abu_simbel": (
        "Abu Simbel Temples",
        "pharaonic",
        "massive rock-cut temples of Ramesses II in Nubia, relocated from Lake Nasser",
    ),
    "abydos_temple": (
        "Abydos Temple",
        "pharaonic",
        "sacred temple with Seti I reliefs and the Abydos King List",
    ),
    "akhenaten": (
        "Akhenaten",
        "artifact",
        "pharaoh who introduced monotheistic Aten worship, Amarna period",
    ),
    "al_azhar_mosque": (
        "Al-Azhar Mosque",
        "islamic",
        "Fatimid mosque and oldest university in Cairo, Islamic learning center",
    ),
    "al_azhar_park": (
        "Al-Azhar Park",
        "modern",
        "modern green park in historic Cairo built over Ayyubid ruins",
    ),
    "al_muizz_street": (
        "Al-Muizz Street",
        "islamic",
        "medieval open-air museum street in Islamic Cairo with mosques and palaces",
    ),
    "amenhotep_iii": (
        "Amenhotep III",
        "artifact",
        "18th Dynasty pharaoh, builder of Luxor Temple additions and the Colossi",
    ),
    "aswan_high_dam": (
        "Aswan High Dam",
        "modern",
        "modern engineering marvel controlling the Nile, created Lake Nasser",
    ),
    "bab_zuweila": ("Bab Zuweila", "islamic", "medieval Fatimid gate in Cairo with twin minarets"),
    "baron_empain_palace": (
        "Baron Empain Palace",
        "modern",
        "Hindu-inspired palace in Heliopolis built by Belgian baron",
    ),
    "bent_pyramid": (
        "Bent Pyramid",
        "pharaonic",
        "Sneferu's pyramid at Dahshur with unique change of angle",
    ),
    "bibliotheca_alexandrina": (
        "Bibliotheca Alexandrina",
        "modern",
        "modern revival of the ancient Library of Alexandria",
    ),
    "cairo_citadel": (
        "Cairo Citadel",
        "islamic",
        "Saladin's medieval fortress on Mokattam Hill overlooking Cairo",
    ),
    "cairo_tower": (
        "Cairo Tower",
        "modern",
        "lotus-flower-shaped tower on Gezira Island panoramic views",
    ),
    "catacombs_of_kom_el_shoqafa": (
        "Catacombs of Kom el-Shoqafa",
        "greco-roman",
        "multi-level Roman burial chambers blending Egyptian and Greek art",
    ),
    "citadel_of_qaitbay": (
        "Citadel of Qaitbay",
        "islamic",
        "15th-century Mamluk fortress in Alexandria on Pharos site",
    ),
    "colossi_of_memnon": (
        "Colossi of Memnon",
        "pharaonic",
        "twin stone statues of Amenhotep III on Luxor west bank",
    ),
    "deir_el_medina": (
        "Deir el-Medina",
        "pharaonic",
        "ancient workers village near Valley of the Kings",
    ),
    "dendera_temple": (
        "Dendera Temple",
        "pharaonic",
        "well-preserved Hathor temple with zodiac ceiling",
    ),
    "edfu_temple": (
        "Edfu Temple",
        "pharaonic",
        "Ptolemaic temple of Horus, best preserved in Egypt",
    ),
    "egyptian_museum_cairo": (
        "Egyptian Museum Cairo",
        "modern",
        "Tahrir Square museum housing Tutankhamun treasures and mummies",
    ),
    "grand_egyptian_museum": (
        "Grand Egyptian Museum",
        "modern",
        "massive new museum near the Pyramids of Giza",
    ),
    "great_pyramids_of_giza": (
        "Great Pyramids of Giza",
        "pharaonic",
        "Khufu Khafre Menkaure pyramids, last ancient wonder standing",
    ),
    "great_sphinx_of_giza": (
        "Great Sphinx of Giza",
        "pharaonic",
        "limestone sphinx with human head and lion body guarding pyramids",
    ),
    "hanging_church": (
        "Hanging Church",
        "greco-roman",
        "Coptic church suspended over Roman gate in Old Cairo",
    ),
    "ibn_tulun_mosque": (
        "Ibn Tulun Mosque",
        "islamic",
        "9th-century Abbasid mosque, oldest intact mosque in Cairo",
    ),
    "karnak_temple": (
        "Karnak Temple",
        "pharaonic",
        "vast Amun-Ra temple complex in Luxor, hypostyle hall",
    ),
    "khan_el_khalili": ("Khan El-Khalili", "islamic", "historic bazaar and souk in medieval Cairo"),
    "king_thutmose_iii": (
        "King Thutmose III",
        "artifact",
        "warrior pharaoh, Napoleon of Egypt, 18th Dynasty military campaigns",
    ),
    "kom_ombo_temple": (
        "Kom Ombo Temple",
        "pharaonic",
        "unique dual temple for Sobek and Horus in Aswan",
    ),
    "luxor_temple": (
        "Luxor Temple",
        "pharaonic",
        "ancient Thebes temple on the east bank of the Nile",
    ),
    "mask_of_tutankhamun": (
        "Mask of Tutankhamun",
        "artifact",
        "gold funerary mask of the boy king, most famous Egyptian artifact",
    ),
    "medinet_habu": (
        "Medinet Habu",
        "pharaonic",
        "mortuary temple of Ramesses III on Luxor west bank",
    ),
    "montaza_palace": (
        "Montaza Palace",
        "modern",
        "royal palace and gardens in Alexandria on the Mediterranean",
    ),
    "muhammad_ali_mosque": (
        "Muhammad Ali Mosque",
        "islamic",
        "alabaster Ottoman mosque dominating the Cairo Citadel skyline",
    ),
    "nefertiti_bust": (
        "Nefertiti Bust",
        "artifact",
        "iconic painted bust of Queen Nefertiti, Amarna art",
    ),
    "philae_temple": (
        "Philae Temple",
        "pharaonic",
        "Isis temple relocated to Agilkia Island in Aswan",
    ),
    "pompeys_pillar": (
        "Pompey's Pillar",
        "greco-roman",
        "tall Roman triumphal column in Alexandria",
    ),
    "pyramid_of_djoser": (
        "Pyramid of Djoser",
        "pharaonic",
        "step pyramid at Saqqara, first monumental stone building",
    ),
    "ramesses_ii": (
        "Ramesses II",
        "artifact",
        "great pharaoh builder of Abu Simbel and the Ramesseum",
    ),
    "ramesseum": ("Ramesseum", "pharaonic", "mortuary temple of Ramesses II on Luxor west bank"),
    "red_pyramid": (
        "Red Pyramid",
        "pharaonic",
        "Sneferu's first true smooth-sided pyramid at Dahshur",
    ),
    "saint_catherine_monastery": (
        "Saint Catherine's Monastery",
        "greco-roman",
        "6th-century Christian monastery at Mount Sinai, Burning Bush",
    ),
    "siwa_oasis": (
        "Siwa Oasis",
        "natural",
        "remote western desert oasis with Oracle of Ammon and salt lakes",
    ),
    "statue_of_tutankhamun": (
        "Statue of Tutankhamun",
        "artifact",
        "gilded wooden statues of the boy pharaoh from his tomb",
    ),
    "sultan_hassan_mosque": (
        "Sultan Hassan Mosque",
        "islamic",
        "imposing Mamluk mosque-madrassa near the Citadel",
    ),
    "temple_of_hatshepsut": (
        "Temple of Hatshepsut",
        "pharaonic",
        "terraced mortuary temple at Deir el-Bahari, female pharaoh",
    ),
    "tomb_of_nefertari": (
        "Tomb of Nefertari",
        "pharaonic",
        "most beautiful tomb in the Valley of the Queens, vivid murals",
    ),
    "unfinished_obelisk": (
        "Unfinished Obelisk",
        "pharaonic",
        "giant unfinished granite obelisk in Aswan quarries",
    ),
    "valley_of_the_kings": (
        "Valley of the Kings",
        "pharaonic",
        "royal necropolis in Luxor west bank with Tutankhamun's tomb",
    ),
    "valley_of_the_queens": (
        "Valley of the Queens",
        "pharaonic",
        "burial site for queens and princes near Luxor",
    ),
    "white_desert": (
        "White Desert",
        "natural",
        "surreal chalk rock formations in Egypt's western desert",
    ),
}

_CATEGORY_MAP: dict[str, str] = {
    "pharaonic": "Pharaonic",
    "islamic": "Islamic",
    "greco-roman": "Greco-Roman",
    "modern": "Modern",
    "natural": "Natural",
    "artifact": "Artifact",
}

_CATEGORY_EMOJI: dict[str, str] = {
    "pharaonic": "🏛️",
    "islamic": "🕌",
    "greco-roman": "🏺",
    "modern": "🏢",
    "natural": "🏜️",
    "artifact": "🗿",
}

# ── Cache prefix ─────────────────────────────────────────────────────────
_SIM_CACHE_PREFIX = "sim_cls:"
_BATCH_SIZE = 10  # how many classes to embed per API call


# ── Cosine similarity ────────────────────────────────────────────────────
def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    ma = math.sqrt(sum(x * x for x in a))
    mb = math.sqrt(sum(x * x for x in b))
    if ma == 0.0 or mb == 0.0:
        return 0.0
    return dot / (ma * mb)


# ── Data class ───────────────────────────────────────────────────────────
@dataclass(frozen=True, slots=True)
class SimilarClass:
    """One similar landmark class with its similarity score."""

    class_name: str
    display_name: str
    category: str
    category_emoji: str
    score: float  # cosine similarity 0.0 - 1.0
    hint: str = ""


# ── Service ──────────────────────────────────────────────────────────────
@dataclass
class ClassSimilarityService:
    """Finds semantically similar landmark classes via Gemini embeddings.

    Uses lazy initialisation: embeddings for all 52 classes are computed
    on the first ``find_similar_classes`` call and cached permanently.
    """

    gemini: GeminiService
    _ready: bool = field(default=False, init=False, repr=False)
    _init_time_ms: float = field(default=0.0, init=False, repr=False)

    # ── helpers ──────────────────────────────────

    @staticmethod
    def _class_to_text(class_name: str) -> str:
        """Build a short text for embedding from class metadata."""
        meta = _CLASS_META.get(class_name)
        if not meta:
            return class_name.replace("_", " ").title()
        display, category, hint = meta
        return f"{display}. Category: {_CATEGORY_MAP.get(category, category)}. {hint}"

    # ── initialisation ───────────────────────────

    async def _ensure_ready(self) -> None:
        """Lazy-init: embed all 52 classes on first use."""
        if self._ready:
            return

        start = time.perf_counter()
        to_embed: list[tuple[str, str]] = []  # (class_name, text)

        for cls in _CLASS_META:
            key = f"{_SIM_CACHE_PREFIX}{cls}"
            if embedding_cache.has(key):
                continue
            to_embed.append((cls, self._class_to_text(cls)))

        if to_embed:
            logger.info("similarity_init_start", classes_to_embed=len(to_embed))
            for i in range(0, len(to_embed), _BATCH_SIZE):
                batch = to_embed[i : i + _BATCH_SIZE]
                texts = [t for _, t in batch]
                try:
                    vectors = await self.gemini.embed(texts, use_cache=False)
                    for j, (cls, _) in enumerate(batch):
                        if j < len(vectors) and vectors[j]:
                            embedding_cache.set(
                                f"{_SIM_CACHE_PREFIX}{cls}",
                                vectors[j],
                                ttl=0,
                            )
                except Exception as exc:
                    logger.warning("similarity_batch_error", error=str(exc))
                    continue

        elapsed = (time.perf_counter() - start) * 1000
        self._init_time_ms = elapsed
        self._ready = True
        cached = sum(1 for c in _CLASS_META if embedding_cache.has(f"{_SIM_CACHE_PREFIX}{c}"))
        logger.info(
            "similarity_init_done",
            cached=cached,
            total=len(_CLASS_META),
            latency_ms=round(elapsed, 1),
        )

    # ── public API ───────────────────────────────

    async def find_similar_classes(
        self,
        class_name: str,
        *,
        top_n: int = 5,
        exclude: set[str] | None = None,
    ) -> list[SimilarClass]:
        """Return the *top_n* most similar classes to *class_name*.

        Uses pre-computed Gemini text embeddings and cosine similarity.
        Falls back to category-based similarity when embeddings are
        unavailable.

        Parameters
        ----------
        class_name:
            The identified landmark class (snake_case).
        top_n:
            Max results to return.
        exclude:
            Additional class names to exclude from results.
        """
        await self._ensure_ready()

        skip = {class_name}
        if exclude:
            skip |= exclude

        query_vec = embedding_cache.get(f"{_SIM_CACHE_PREFIX}{class_name}")

        if query_vec:
            # ── embedding-based similarity ───────
            scored: list[tuple[str, float]] = []
            for cls in _CLASS_META:
                if cls in skip:
                    continue
                vec = embedding_cache.get(f"{_SIM_CACHE_PREFIX}{cls}")
                if vec is None:
                    continue
                sim = _cosine_sim(query_vec, vec)
                scored.append((cls, sim))

            scored.sort(key=lambda x: x[1], reverse=True)
            results: list[SimilarClass] = []
            for cls, sim in scored[:top_n]:
                meta = _CLASS_META.get(cls)
                if meta:
                    display, cat, hint = meta
                    results.append(
                        SimilarClass(
                            class_name=cls,
                            display_name=display,
                            category=_CATEGORY_MAP.get(cat, cat),
                            category_emoji=_CATEGORY_EMOJI.get(cat, ""),
                            score=round(sim, 4),
                            hint=hint,
                        )
                    )
            return results

        # ── fallback: category matching ──────────
        logger.warning("similarity_no_embedding", class_name=class_name)
        return self._category_fallback(class_name, skip, top_n)

    def _category_fallback(
        self,
        class_name: str,
        skip: set[str],
        top_n: int,
    ) -> list[SimilarClass]:
        """Simple category-based matching when embeddings aren't ready."""
        query_meta = _CLASS_META.get(class_name)
        if not query_meta:
            return []
        _, query_cat, _ = query_meta

        results: list[SimilarClass] = []
        for cls, (display, cat, hint) in _CLASS_META.items():
            if cls in skip:
                continue
            score = 0.7 if cat == query_cat else 0.3
            results.append(
                SimilarClass(
                    class_name=cls,
                    display_name=display,
                    category=_CATEGORY_MAP.get(cat, cat),
                    category_emoji=_CATEGORY_EMOJI.get(cat, ""),
                    score=score,
                    hint=hint,
                )
            )

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_n]

    # ── info / stats ─────────────────────────────

    def get_class_meta(self, class_name: str) -> dict | None:
        """Return static metadata for a class."""
        meta = _CLASS_META.get(class_name)
        if not meta:
            return None
        display, cat, hint = meta
        return {
            "class_name": class_name,
            "display_name": display,
            "category": _CATEGORY_MAP.get(cat, cat),
            "category_emoji": _CATEGORY_EMOJI.get(cat, ""),
            "hint": hint,
        }

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def total_classes(self) -> int:
        return len(_CLASS_META)

    @property
    def cached_count(self) -> int:
        return sum(1 for c in _CLASS_META if embedding_cache.has(f"{_SIM_CACHE_PREFIX}{c}"))
