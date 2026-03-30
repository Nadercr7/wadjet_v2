# STORIES ENRICHMENT PLAN — Real History + Smart Images + Narration

> Goal: Transform 5 mythology stories into historically accurate, interactive experiences.

---

## Current Stories Inventory

| # | File | Title | Chapters | Issue |
|---|------|-------|----------|-------|
| 1 | `the_eye_of_horus.json` | The Eye of Horus | 5 | Mythologically accurate but thin on detail |
| 2 | `the_book_of_thoth.json` | The Book of Thoth | 5 | Engaging but missing historical context |
| 3 | `the_journey_of_ra.json` | The Journey of Ra | 5 | Good structure, needs Duat geography |
| 4 | `the_weighing_of_the_heart.json` | The Weighing of the Heart | 5 | Core myth, needs Papyrus of Ani references |
| 5 | `the_tears_of_isis.json` | The Tears of Isis | 5 | Emotional, needs more ritual context |

---

## Historical Sources for Enrichment

| Source | Period | Use For |
|--------|--------|---------|
| Pyramid Texts | ~2400 BCE | Earliest spells, Ra's journey, royal afterlife |
| Coffin Texts | ~2100 BCE | Middle Kingdom magic, Thoth's role |
| Book of the Dead | ~1550 BCE | Weighing of the Heart (Spell 125), Am-Duat |
| Papyrus of Ani | ~1250 BCE | Illustrated afterlife journey |
| Great Harris Papyrus | ~1150 BCE | Temple donations, festival descriptions |
| Contendings of Horus & Set | ~1150 BCE | Full Horus-Set conflict narrative |
| Westcar Papyrus | ~1700 BCE | Tales of magic and wonder |
| Temple of Dendera | Ptolemaic | Eye of Horus restoration myth, Hathor |
| Temple of Edfu | Ptolemaic | Horus victory over Set |
| Metternich Stela | ~380 BCE | Isis's healing magic |

---

## Rewrite Guidelines

Each story should follow this structure:

```json
{
  "id": "the_eye_of_horus",
  "title": "The Eye of Horus",
  "title_ar": "عين حورس",
  "description": "One-sentence hook",
  "period": "New Kingdom, ~1250 BCE",
  "source": "Contendings of Horus and Set, Papyrus Chester Beatty I",
  "difficulty": "intermediate",
  "duration_minutes": 15,
  "cover_image_prompt": "...",
  "chapters": [
    {
      "index": 0,
      "title": "Chapter Title",
      "title_ar": "العنوان",
      "text": "2-3 paragraphs of historically accurate narrative...",
      "text_ar": "النص العربي...",
      "image_prompt": "Specific scene description for FLUX.1...",
      "glyphs": [
        {
          "gardiner": "D10",
          "unicode": "𓂀",
          "name": "Eye of Horus (Wedjat)",
          "transliteration": "wḏꜣt",
          "meaning": "The restored eye, symbol of healing and protection",
          "context": "The Wedjat eye appears in this chapter as Horus recovers his sight..."
        }
      ],
      "interaction": {
        "type": "quiz",
        "question": "What did Thoth use to restore Horus's eye?",
        "options": ["Magic spells", "Sacred herbs", "Moonlight", "Divine saliva"],
        "correct": 0,
        "explanation": "According to the Contendings of Horus and Set..."
      },
      "narration_voice": "Aoede"
    }
  ],
  "glyph_summary": ["D10", "C12", "G5", ...],
  "total_glyphs": 12
}
```

---

## Story Rewrites (Detailed)

### Story 1: The Eye of Horus (Wedjat)

**Source**: Contendings of Horus and Set (Papyrus Chester Beatty I, ~1150 BCE)

**Chapters**:
1. **The Murder of Osiris** — Set's jealousy, the coffin trick, Isis's search
2. **The Birth of Horus** — Isis hides in the papyrus marshes of Khemmis
3. **The Contendings** — 80 years of trials before the Ennead
4. **The Eye is Lost** — Set tears out Horus's eye during battle
5. **The Restoration** — Thoth restores the Wedjat, Horus offers it to Osiris
6. **The Judgment** — Horus crowned King of the Living, Set given the desert

**Key Glyphs**: 𓂀 (Wedjat D10), 𓁥 (Set C7), 𓁣 (Horus C10), 𓁦 (Osiris A40), 𓊨 (Isis throne Q1)

### Story 2: The Book of Thoth

**Source**: Setne Khamwas cycle (Demotic, ~300 BCE, based on older traditions)

**Chapters**:
1. **The Scholar Prince** — Prince Setne Khamwas seeks the Book at Coptos
2. **The Guardian** — The book is guarded by an immortal serpent, the deathless snake
3. **The Warning of Neferkaptah** — Ghost of previous owner tells his tragic tale
4. **The Prize** — Setne takes the book, gains power over heaven and earth
5. **The Curse** — Thoth's punishment: illusions, loss, madness
6. **The Return** — Setne returns the book to Neferkaptah's tomb

**Key Glyphs**: 𓁟 (Thoth C3), 𓏛 (book Y1), 𓆓 (cobra I9), 𓊖 (city O49)

### Story 3: The Journey of Ra

**Source**: Book of Gates, Amduat (KV17 Seti I tomb, ~1280 BCE)

**Chapters**:
1. **The Western Horizon** — Ra enters the Duat at sunset
2. **The First Gates** — Passage through caverns, awakening the dead
3. **The Realm of Sokar** — Deepest underworld, sand desert of silence
4. **The Serpent Apophis** — The great enemy attacks Ra's barque
5. **The Magic of Isis and Set** — Even Set helps fight Apophis (paradox)
6. **The Rebirth** — Ra emerges from Nut's body as Khepri at dawn

**Key Glyphs**: 𓇳 (Ra sun N5), 𓆗 (serpent I10), 𓇯 (sky N1), 𓆣 (scarab L1)

### Story 4: The Weighing of the Heart

**Source**: Book of the Dead, Spell 125 (Papyrus of Ani, ~1250 BCE)

**Chapters**:
1. **The Negative Confession** — The deceased recites 42 sins they did not commit
2. **The Hall of Two Truths** — Maat's feather vs. the heart on the scales
3. **The 42 Assessor Gods** — Each god tests a specific virtue
4. **The Weighing** — Anubis operates the scales, Thoth records
5. **Ammit Waits** — The Devourer of the Dead lurks if the heart is heavy
6. **The Field of Reeds** — The justified enters paradise (Sekhet-Aaru)

**Key Glyphs**: 𓂋 (heart F34), 𓁶 (Maat C10), 𓁢 (Anubis C6), 𓇋 (feather H6)

### Story 5: The Tears of Isis

**Source**: Great Hymn to Osiris (Stela of Amenmose, 18th Dynasty, ~1500 BCE)

**Chapters**:
1. **The Queen of Heaven** — Isis's power and knowledge among the gods
2. **The Search for Osiris** — Isis travels to Byblos following the djed pillar
3. **The Reassembly** — Isis and Nephthys gather Osiris's scattered body
4. **The Conception** — Isis conceives Horus from the restored Osiris
5. **The Tears** — Isis's weeping causes the Nile's annual flood (Wep Renpet)
6. **The Eternal Mother** — Isis as protector, her cult across the Mediterranean

**Key Glyphs**: 𓊨 (Isis throne Q1), 𓊽 (djed pillar R11), 𓇗 (Nile N36), 𓆇 (cobra D42)

---

## Image Generation Strategy

### Art Style Prompt Template

```
"Ancient Egyptian papyrus illustration of [SCENE], painted in rich golden 
and amber tones with deep lapis lazuli blue accents, intricate hieroglyphic 
border frame, style of New Kingdom tomb painting blended with Art Deco 
elegance, detailed ink work on aged yellowed papyrus texture, museum-quality 
archaeological artifact illustration, dramatic lighting, 16:9 aspect ratio"
```

### Style Consistency Rules

1. **Color palette**: Gold (#D4AF37), amber, lapis blue (#1A237E), papyrus cream
2. **Composition**: Central subject, hieroglyphic border frame
3. **Figures**: Egyptian profile pose (canonical), not Western frontal
4. **Text**: Hieroglyphs as decorative elements, not readable (to avoid errors)
5. **Atmosphere**: Warm, reverent, museum-quality

### Model Selection

| Model | Resolution | Speed | Quality | Use |
|-------|-----------|-------|---------|-----|
| FLUX.1 schnell | 1024×1024 | ~2s | Good | Primary — most scenes |
| SDXL | 1024×1024 | ~5s | Better | Fallback, or detailed covers |

### Caching Strategy

```
app/static/cache/images/
├── stories/
│   ├── the_eye_of_horus/
│   │   ├── cover.webp
│   │   ├── chapter_0.webp
│   │   ├── chapter_1.webp
│   │   └── ...
│   ├── the_book_of_thoth/
│   └── ...
```

- Generate on first request, cache forever
- WebP format for smaller file size
- Serve with cache-control: max-age=31536000
- Pre-generate cover images during deployment (optional script)

---

## Narration Integration

### Voice Assignment

| Context | Voice | Model |
|---------|-------|-------|
| Stories (narration) | Aoede | Gemini 2.5 Flash TTS |
| Thoth dialogue within stories | Orus | Gemini 2.5 Flash TTS |
| Arabic narration | Aoede (Arabic) | Gemini 2.5 Flash TTS |

### Narration Flow

1. User opens chapter → text displayed
2. "Listen" button (🔊) at top of chapter
3. Click → POST /api/tts with chapter text + voice
4. Audio cached at `/static/cache/audio/stories/{story_id}/chapter_{n}.mp3`
5. Subsequent visits → serve cached audio
6. Auto-advance: after narration ends, subtle "Next Chapter" prompt

### Audio Caching

```
app/static/cache/audio/
├── stories/
│   ├── the_eye_of_horus/
│   │   ├── chapter_0_en.mp3
│   │   ├── chapter_0_ar.mp3
│   │   └── ...
```

---

## Interactive Elements

### Quiz Questions (1 per chapter)
- Multiple choice (4 options)
- Based on chapter content
- Correct answer includes historical explanation
- Score tracked in StoryProgress table

### Choice Points (1-2 per story)
- Branch the narrative briefly (e.g., "Do you enter the tomb or wait?")
- Both paths converge (not a branching tree)
- Adds replay value

### Glyph Annotations
- Inline glyph highlights: hover/tap to see meaning
- "Glyphs Learned" counter per story
- Links to dictionary entry for each glyph

---

## Potential New Stories (Phase 4 Stretch Goal)

| # | Title | Period | Theme |
|---|-------|--------|-------|
| 6 | The Building of the Great Pyramid | Old Kingdom, ~2560 BCE | Engineering, labor organization, Khufu |
| 7 | Akhenaten's Revolution | New Kingdom, ~1350 BCE | Monotheism, Aten worship, religious conflict |
| 8 | The Battle of Kadesh | New Kingdom, ~1274 BCE | Ramesses II vs. Hittites, peace treaty |

These are research candidates only — implement if time permits during Phase 4.

---

## Test Plan

| # | Test | Expected |
|---|------|----------|
| 1 | Load story listing page | All 5 stories with covers |
| 2 | Open a story | First chapter text + image loads |
| 3 | Navigate chapters | Forward/back works, progress saved |
| 4 | Click glyph annotation | Popup with meaning + Gardiner code |
| 5 | Answer quiz question | Correct/incorrect feedback shown |
| 6 | Play narration | Audio plays, "listening" state shown |
| 7 | Story image generation | Image appears (or cached version) |
| 8 | Complete a story | Progress saved to DB, "completed" badge |
