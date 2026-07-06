# Phase 8 — Stories of the Nile (Quiz Replacement)

## Goal
Replace the broken quiz with "Stories of the Nile" — an interactive Egyptian mythology storytelling experience that teaches hieroglyphs through narrative context. This is the most significant new feature in v3.

## Why Replace Quiz?
The current quiz has fundamental issues:
- Answers exposed client-side (C3, partially fixed in Phase 1)
- Deterministic seed (M14, fixed in Phase 1)
- Dedup infinite loop (H3, fixed in Phase 1)
- Only ~20 static questions → boring after 2 minutes
- Rote memorization — low engagement, no replay value

Stories are better because:
- Contextual learning (hieroglyphs encountered naturally in narratives)
- Hours of content (13 stories, multiple chapters each)
- 4 interaction types (variety keeps engagement)
- High replay value and shareability
- Deep cultural immersion

## New Features
- 5 Egyptian mythology stories (Tier 1 — expandable to 13)
- 4 interactive learning types per story
- **AI-Generated Illustrations**: Each chapter gets scene images via Cloudflare FLUX.1 schnell
- **Narrative Voice**: Full chapter narration using Gemini 2.5 Flash TTS (`Aoede` voice for myths)
- **Cinematic Animations**: Ken Burns effect (zoom + pan) on AI images between story sections
- Progress tracking per story and overall
- Offline-capable (story JSON + generated images cached in SW)
- Bilingual support (English + Arabic)

## Files Created
- `data/stories/` — story JSON files
- `data/stories/osiris-myth.json`
- `data/stories/journey-of-ra.json`
- `data/stories/creation-from-nun.json`
- `data/stories/eye-of-ra.json`
- `data/stories/contendings-horus-set.json`
- `app/core/stories_engine.py` — story loader, progress tracker
- `app/core/image_service.py` — AI image generation with Cloudflare FLUX fallback chain
- `app/core/tts_service.py` — TTS with Gemini → Groq → Browser fallback (shared across all pages)
- `app/api/stories.py` — story API endpoints
- `app/api/media.py` — media generation endpoints (TTS + images)
- `app/templates/stories.html` — story listing page
- `app/templates/story_reader.html` — reading + interaction UI + narration controls
- `app/templates/partials/story_card.html` — story list card
- `app/static/cache/images/` — cached AI-generated images
- `app/static/cache/audio/` — cached TTS narration audio

## Files Modified
- `app/templates/partials/nav.html` — rename "Quiz" → "Stories" / "حكايات"
- `app/static/sw.js` — add story routes to pre-cache
- `app/main.py` — mount stories router
- `app/api/pages.py` — add /stories and /stories/:id page routes

## Story Data Structure
```json
{
    "id": "osiris-myth",
    "title": { "en": "The Osiris Myth", "ar": "أسطورة أوزيريس" },
    "subtitle": { "en": "Death, resurrection, and the throne of Egypt", "ar": "الموت والبعث وعرش مصر" },
    "cover_glyph": "𓊨",
    "difficulty": "beginner",
    "estimated_minutes": 15,
    "glyphs_taught": ["Q1", "N5", "S34", "G14", "C7", "E20", "R8"],
    "chapters": [
        {
            "index": 0,
            "title": { "en": "The Golden Age", "ar": "العصر الذهبي" },
            "scene_image_prompt": "Ancient Egyptian golden throne room with Osiris seated as pharaoh, golden sand, hieroglyphs on walls, warm dramatic lighting, oil painting style",
            "tts_voice": "Aoede",
            "tts_style": "Narrate as an ancient Egyptian storyteller, slow pace, mysterious and reverent tone",
            "paragraphs": [
                {
                    "text": {
                        "en": "In the beginning, Osiris ruled as the first pharaoh of Egypt. He taught humanity the arts of agriculture, law, and worship of the gods.",
                        "ar": "في البداية، حكم أوزيريس كأول فرعون لمصر. علّم البشر فنون الزراعة والقانون وعبادة الآلهة."
                    },
                    "glyph_annotations": [
                        {
                            "word": { "en": "Osiris", "ar": "أوزيريس" },
                            "gardiner_code": "Q1",
                            "glyph": "𓊨",
                            "meaning": { "en": "Seat/throne — the hieroglyph for Osiris's name", "ar": "العرش — الهيروغليفية لاسم أوزيريس" },
                            "transliteration": "wsjr"
                        }
                    ]
                }
            ],
            "interactions": [
                {
                    "type": "glyph_discovery",
                    "after_paragraph": 0,
                    "glyph": "Q1",
                    "prompt": { "en": "You just met Osiris! Tap his hieroglyph to learn it.", "ar": "قابلت أوزيريس! اضغط على الهيروغليفية لتتعلمها." }
                },
                {
                    "type": "choose_glyph",
                    "after_paragraph": 2,
                    "question": { "en": "Which hieroglyph represents the sun god Ra?", "ar": "أي هيروغليفية تمثل إله الشمس رع؟" },
                    "options": ["N5", "S34", "G14", "M17"],
                    "correct": "N5",
                    "explanation": { "en": "The sun disk (N5) represents Ra, the supreme solar deity.", "ar": "قرص الشمس (N5) يمثل رع، إله الشمس الأعلى." }
                },
                {
                    "type": "write_word",
                    "after_paragraph": 4,
                    "target_word": { "en": "life", "ar": "حياة" },
                    "target_glyph": "𓋹",
                    "gardiner_code": "S34",
                    "hint": { "en": "The most famous Egyptian symbol", "ar": "أشهر رمز مصري" }
                }
            ]
        }
    ]
}
```

## Stories Engine (app/core/stories_engine.py)
```python
import json
from pathlib import Path
from functools import lru_cache

STORIES_DIR = Path("data/stories")

@lru_cache(maxsize=1)
def load_all_stories() -> list[dict]:
    """Load all story metadata (without full chapters) for listing."""
    stories = []
    for f in sorted(STORIES_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        stories.append({
            "id": data["id"],
            "title": data["title"],
            "subtitle": data["subtitle"],
            "cover_glyph": data["cover_glyph"],
            "difficulty": data["difficulty"],
            "estimated_minutes": data["estimated_minutes"],
            "chapter_count": len(data["chapters"]),
            "glyphs_taught": data["glyphs_taught"],
        })
    return stories

def load_story(story_id: str) -> dict | None:
    """Load full story with all chapters."""
    path = STORIES_DIR / f"{story_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

def get_chapter(story_id: str, chapter_index: int) -> dict | None:
    """Load a specific chapter from a story."""
    story = load_story(story_id)
    if not story or chapter_index >= len(story["chapters"]):
        return None
    return story["chapters"][chapter_index]
```

## API Endpoints (app/api/stories.py)
```python
# GET /api/stories — list all stories (metadata only)
# GET /api/stories/{story_id} — full story with chapters
# GET /api/stories/{story_id}/chapters/{index} — single chapter
# POST /api/stories/{story_id}/interact — submit interaction answer
# GET /api/stories/{story_id}/progress — user progress (auth required)
# POST /api/stories/{story_id}/progress — update progress (auth required)
```

## AI Image Generation Service (app/core/image_service.py)
```python
import httpx
import hashlib
from pathlib import Path

CACHE_DIR = Path("app/static/cache/images")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Cloudflare Workers AI config — uses existing CF account
CF_ACCOUNT_ID = settings.cloudflare_account_id
CF_API_TOKEN = settings.cloudflare_api_token
CF_FLUX_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/black-forest-labs/FLUX-1-schnell"
CF_SDXL_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/@cf/stabilityai/stable-diffusion-xl-base-1.0"

EGYPTIAN_STYLE_SUFFIX = ", ancient Egyptian art style, golden sand, hieroglyphs, dramatic warm lighting, detailed oil painting"

async def generate_story_image(prompt: str, story_id: str, chapter_idx: int) -> str | None:
    """Generate scene image for a story chapter. Returns static file path or None."""
    cache_key = hashlib.sha256(f"{story_id}-{chapter_idx}-{prompt}".encode()).hexdigest()[:16]
    cache_path = CACHE_DIR / f"{cache_key}.png"

    if cache_path.exists():
        return f"/static/cache/images/{cache_key}.png"

    full_prompt = prompt + EGYPTIAN_STYLE_SUFFIX

    # Try FLUX.1 schnell first (fastest)
    image_bytes = await _try_cloudflare(CF_FLUX_URL, full_prompt)
    if not image_bytes:
        # Fallback to SDXL
        image_bytes = await _try_cloudflare(CF_SDXL_URL, full_prompt)

    if image_bytes:
        cache_path.write_bytes(image_bytes)
        return f"/static/cache/images/{cache_key}.png"

    return None  # UI shows placeholder

async def _try_cloudflare(url: str, prompt: str) -> bytes | None:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {CF_API_TOKEN}"},
                json={"prompt": prompt, "num_steps": 4}  # schnell optimized for 4 steps
            )
            if resp.status_code == 200:
                return resp.content
    except Exception:
        pass
    return None
```

## TTS Narration Service (app/core/tts_service.py)
```python
import hashlib
import wave
from pathlib import Path
from google import genai
from google.genai import types

AUDIO_CACHE = Path("app/static/cache/audio")
AUDIO_CACHE.mkdir(parents=True, exist_ok=True)

# Voice presets for different contexts
VOICE_PRESETS = {
    "story_narration": {"voice": "Aoede", "style": "Ancient storyteller, reverent and mysterious"},
    "thoth_chat": {"voice": "Orus", "style": "Ancient Egyptian deity, authoritative and wise"},
    "landing": {"voice": "Charon", "style": "Welcoming museum guide, informative and warm"},
    "dictionary": {"voice": "Rasalgethi", "style": "Academic lecturer, clear and precise"},
}

async def speak(text: str, lang: str = "en", context: str = "default") -> str | None:
    """Generate TTS audio. Returns static file path or None."""
    preset = VOICE_PRESETS.get(context, {"voice": "Charon", "style": "Clear and natural"})
    cache_key = hashlib.sha256(f"{text[:200]}-{lang}-{preset['voice']}".encode()).hexdigest()[:16]
    cache_path = AUDIO_CACHE / f"{cache_key}.wav"

    if cache_path.exists():
        return f"/static/cache/audio/{cache_key}.wav"

    # Try Gemini TTS (primary — FREE, highest quality)
    audio = await _try_gemini_tts(text, lang, preset)
    if not audio:
        # Try Groq Orpheus (fallback — FREE)
        audio = await _try_groq_tts(text, lang)

    if audio:
        cache_path.write_bytes(audio)
        return f"/static/cache/audio/{cache_key}.wav"

    return None  # Frontend falls back to browser SpeechSynthesis

async def _try_gemini_tts(text: str, lang: str, preset: dict) -> bytes | None:
    try:
        client = genai.Client(api_key=get_next_gemini_key())
        prompt = f"""
        DIRECTOR'S NOTES:
        Style: {preset['style']}
        Language: {lang}

        TRANSCRIPT:
        {text}
        """
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=preset["voice"],
                        )
                    )
                ),
            )
        )
        return response.candidates[0].content.parts[0].inline_data.data
    except Exception:
        return None

async def _try_groq_tts(text: str, lang: str) -> bytes | None:
    try:
        model = "playai-tts-arabic" if lang == "ar" else "playai-tts"
        # ... Groq TTS implementation using existing Groq integration
        pass
    except Exception:
        return None
```

## Frontend Design

### Story List Page (`stories.html`)
- Grid of story cards with cover glyph, title, difficulty badge
- Progress indicator per story (if logged in)
- Filter by difficulty: Beginner / Intermediate / Advanced
- Bilingual titles

### Story Reader (`story_reader.html`)
- Full-page reading mode (dark background, comfortable typography)
- **Hero image** at top of each chapter — AI-generated scene with Ken Burns animation (slow zoom + pan CSS)
- **Narration controls**: Play/Pause button at bottom-right, auto-advances with text highlight
- Chapter navigation (prev/next)
- Paragraphs flow naturally, glyph annotations glow gold inline
- Interaction panels slide in between paragraphs
- Progress bar at top showing chapter completion
- "Glyphs Learned" counter
- **Image loading**: spinner while AI generates, cached for subsequent visits

### Ken Burns Animation (CSS)
```css
@keyframes ken-burns {
    0% { transform: scale(1) translate(0, 0); }
    100% { transform: scale(1.1) translate(-2%, -1%); }
}
.story-hero-image {
    animation: ken-burns 20s ease-in-out infinite alternate;
    object-fit: cover;
    width: 100%;
    height: 300px;
    border-radius: 12px;
}
```

### Narration UI
```html
<!-- Floating narration control -->
<div class="fixed bottom-6 right-6 z-50" x-data="{ playing: false }">
    <button @click="toggleNarration()" class="w-14 h-14 rounded-full bg-gold/20 border border-gold/50 backdrop-blur-xl flex items-center justify-center shadow-lg hover:bg-gold/30 transition">
        <span x-show="!playing" class="text-2xl">🔊</span>
        <span x-show="playing" class="text-2xl">⏸️</span>
    </button>
</div>
```

### Interaction UIs

**Glyph Discovery**: Gold-bordered card with large glyph, transliteration, meaning. Tap → "Mark as learned ✓"

**Choose the Glyph**: 4 option cards in 2x2 grid. Tap correct → green + explanation. Tap wrong → red + hint.

**Write the Word**: Input field with hieroglyph keyboard, or drag-and-drop glyph selection.

**Story Decision**: 2-3 narrative choices as full-width buttons. Non-wrong (educational branching, not changing the actual myth).

## Testing Checklist
- [ ] /stories page shows 5 story cards
- [ ] Each card shows: title, subtitle, cover glyph, difficulty, chapter count
- [ ] Click story → opens reader with first chapter
- [ ] **AI image loads at top of chapter** (or shows placeholder if API fails)
- [ ] **Ken Burns animation plays on chapter image** (slow zoom + pan)
- [ ] **Narration button (🔊) visible at bottom-right**
- [ ] **Click narration → plays TTS audio of chapter text**
- [ ] **TTS audio uses Gemini TTS when online** (check Network tab for gemini API call)
- [ ] **TTS falls back to Groq → Browser if Gemini fails**
- [ ] Story text renders in correct language (en/ar based on lang)
- [ ] Glyph annotations glow gold inline in text
- [ ] Glyph Discovery: tap glyph → shows details, "Mark as learned"
- [ ] Choose the Glyph: 4 options, correct = green, wrong = red + explanation
- [ ] Write the Word: input accepts hieroglyph, validates against target
- [ ] Navigate between chapters (next/prev)
- [ ] Progress bar updates as chapters are completed
- [ ] Logged-in user: progress persists across sessions (DB)
- [ ] Guest user: progress in localStorage (ephemeral)
- [ ] **Offline: stories + cached images + cached audio load from SW cache**
- [ ] Arabic: story content displays in Arabic with RTL
- [ ] **Arabic TTS: narration plays in Arabic when lang=ar**
- [ ] Nav: "Stories" replaces "Quiz" (or "حكايات" in Arabic)
- [ ] Mobile: reading mode comfortable, interactions touch-friendly
- [ ] **Generated images cached (second visit loads instantly from `/static/cache/images/`)**
- [ ] **Generated audio cached (second listen loads from `/static/cache/audio/`)**

## Git Commit
```
[Phase 8] Stories of the Nile — 5 stories, AI illustrations (FLUX), narrative TTS (Gemini), Ken Burns animations
```
