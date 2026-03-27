# Wadjet v2 — Expansion Plan (4 Tasks + Deployment)

> **Created**: 2026-03-25
> **Status**: PLANNING COMPLETE — Ready for execution
> **Last Updated**: 2026-03-27

---

## Self-Prompt (Read this at the start of each session)

```
READ THIS FILE FIRST. You are continuing the Wadjet v2 Expansion Plan.
Check the STATUS of each task below. Find the first NOT STARTED or IN PROGRESS task.
Read its detailed spec, then execute it. When done, update the status here.
After each task, update the "Progress Log" section at the bottom of this file.
```

---

## Task Overview

| # | Task | Status | Complexity | Files Affected |
|---|------|--------|------------|----------------|
| T1 | Thoth Chat Formatting & Colors Fix | DONE ✅ | Small | chat.html, input.css, thoth_chat.py |
| T2 | Explore: Full Egypt Heritage Expansion | DONE ✅ | Large | expanded_sites.json, data/text/*.json, explore.py (api), landmarks.py (core), explore.html |
| T2.2 | Explore: Deep Content, Images & Coverage | DONE ✅ | Large | expanded_sites.json, sites_data/*.py, build_expanded_sites.py, populate_images.py |
| T3 | Dictionary: Complete Gardiner Sign List | DONE ✅ | Large | gardiner_data/ (26 files), gardiner.py, dictionary.py (api), dictionary.html |
| T3.1 | Dictionary: UX Overhaul & Learning Journey | DONE ✅ | Medium | dictionary.py (api), dictionary.html |
| T3.2 | Dictionary: Premium Learning Experience | DONE ✅ | Large | dictionary.py (api), dictionary.html, input.css, lesson_page.html (NEW) |
| T4 | Write Page: Fix & Real Translation | PHASE 1 DONE ✅ | Large | write.html, write.py, gardiner.py, egyptian_lexicon.jsonl (NEW) |
| T5 | Landmark AI Experience & Quality | NOT STARTED | Medium | explore.py (api), landmark_pipeline.py, explore.html, landmarks.html |

---

## T1: Thoth Chat Formatting & Colors Fix

### Status: DONE ✅

### Problem
- Chat text colors/formatting aren't optimal for readability
- The `renderMarkdown()` JS function is custom/fragile
- Bold text uses gold (#D4AF37) which can be hard to read
- Italic text uses sand (#C4A265) which is too muted
- Lists don't have proper spacing
- Headers and body text could have better contrast
- No table rendering support in renderMarkdown

### Changes Needed

1. **input.css (chat styles ~L133-220)**:
   - Increase body text luminosity for better readability (ivory #F5F0E8)
   - Headers: H1 gold stays, H2 gold-light, H3 ivory — better hierarchy
   - Bold: keep gold but ensure it's distinct from headers
   - Italic: use ivory-muted instead of sand
   - Lists: better spacing (margin-bottom: 0.3rem per li)
   - Code blocks: slightly brighter background for contrast
   - Add `.chat-table` styles for markdown tables
   - Blockquote: slightly more visible border

2. **chat.html renderMarkdown()**:
   - Add table rendering (| col | col |)
   - Fix bold/italic inside list items (currently parsed AFTER block, misses some)
   - Add `**text**` inside `<li>` support
   - Better empty line handling

3. **thoth_chat.py**:
   - Review system prompt formatting instructions — make sure Thoth uses markdown well

### References
- Current CSS: `app/static/css/input.css` lines 133-220
- Current renderer: `app/templates/chat.html` lines ~280-395 (renderMarkdown function)
- System prompt: `app/core/thoth_chat.py` lines ~33-48

### Detailed Implementation Steps

#### Step 1: Fix Chat CSS (`app/static/css/input.css` lines 133-220)

Current structure:
```css
.chat-content { ... }           /* base container */
.chat-content .chat-h1 { ... }  /* H1: Playfair Display, #D4AF37 */
.chat-content .chat-h2 { ... }  /* H2: same gold */
.chat-content .chat-h3 { ... }  /* H3: same gold */
.chat-content .chat-bold { ... } /* Bold: #D4AF37, w600 */
.chat-content .chat-italic { ... } /* Italic: #C4A265 */
.chat-content ul, ol { ... }    /* Lists */
.chat-content blockquote { ... } /* Blockquote */
.chat-content pre { ... }       /* Code block */
.chat-content code { ... }      /* Inline code */
```

Changes to make:
- `.chat-content p` — ADD rule: `color: var(--color-ivory); line-height: 1.75;`
- `.chat-h1` — keep `#D4AF37`, add `border-bottom: 1px solid rgba(212,175,55,0.2); padding-bottom: 0.5rem;`
- `.chat-h2` — change to `color: var(--color-gold-light, #E5C76B);`
- `.chat-h3` — change to `color: var(--color-ivory, #F5F0E8); font-weight: 600;`
- `.chat-bold` — change to `color: #E5C76B; font-weight: 700;` (gold-light, not same as H1)
- `.chat-italic` — change to `color: #F5F0E8; font-style: italic; opacity: 0.85;`
- `ul li, ol li` — add `margin-bottom: 0.3rem;`
- `blockquote` — change border to `4px solid rgba(212,175,55,0.4);` + `background: rgba(212,175,55,0.05);`
- ADD new `.chat-table` styles:
  ```css
  .chat-content table { width: 100%; border-collapse: collapse; margin: 1rem 0; }
  .chat-content th { background: rgba(212,175,55,0.15); color: #D4AF37; padding: 0.5rem; text-align: left; border-bottom: 2px solid rgba(212,175,55,0.3); }
  .chat-content td { padding: 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.1); color: #F5F0E8; }
  .chat-content tr:hover { background: rgba(212,175,55,0.05); }
  ```

#### Step 2: Fix renderMarkdown (`app/templates/chat.html` ~L280-395)

Function signature: `renderMarkdown(text)` inside `chatApp()` Alpine component.

Current flow:
1. Fenced code blocks (``` → `<pre><code>`)
2. Inline code (`` ` `` → `<code>`)
3. Headers (###, ##, #)
4. HR (---)
5. Blockquotes (>)
6. Unordered lists (- or *)
7. Ordered lists (1. or 1))
8. Bold (**text**)
9. Italic (*text*)

Additions needed:
- **Table parsing**: After HR, before blockquote. Detect lines with `|`. Parse header row, separator row (`---`), data rows. Generate `<table><thead><tr><th>...</th></tr></thead><tbody><tr><td>...</td></tr></tbody></table>`.
- **Bold inside lists**: Move bold/italic regex BEFORE the list-item wrapping OR apply inline formatting inside the `<li>` content.
- **Empty line handling**: Consolidate multiple blank lines into single `<br>`.

Add this table parser (insert after HR block detection, before blockquote):
```javascript
// Table detection
if (line.includes('|') && line.trim().startsWith('|')) {
  // Collect all consecutive | lines into a table block
  // Parse first row as headers, skip separator, rest as data
}
```

#### Step 3: Review System Prompt (`app/core/thoth_chat.py` ~L33-48)

`SYSTEM_PROMPT` constant defines Thoth's personality. Check if it instructs Thoth to:
- Use markdown formatting (headers, bold, lists)
- Keep responses structured
- Use tables when presenting comparative info

If not, add a formatting instruction line like:
```
Format your responses with markdown: use **bold** for key terms, bullet lists for multiple points, and tables (| col |) when comparing items.
```

#### After T1 is complete:
```bash
cd "D:\Personal attachements\Projects\Final_Horus\Wadjet-v2"
npm run build
# Bump cache version in base.html: ?v=15 → ?v=16
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Test: open http://localhost:8000/chat and ask Thoth a question
# Verify: headers have hierarchy, bold is distinct, tables render, lists are spaced
```

### T1 Self-Prompt (copy this when starting T1)
```
I'm working on Wadjet v2, Task T1: Fix Thoth Chat Formatting & Colors.
Read planning/EXPANSION_PLAN.md for the full plan.

Files to modify:
1. app/static/css/input.css (lines 133-220) — fix chat CSS colors/spacing
2. app/templates/chat.html (lines 280-395) — fix renderMarkdown() function
3. app/core/thoth_chat.py (lines 33-48) — review system prompt

Key changes:
- Better color hierarchy: H1 gold, H2 gold-light, H3 ivory, body ivory
- Bold uses gold-light (#E5C76B) not same gold as H1
- Italic uses ivory with 0.85 opacity
- Add table rendering to renderMarkdown()
- Add .chat-table CSS styles
- Better list spacing (0.3rem margin per li)
- Stronger blockquote border

After changes: npm run build, bump ?v=15 → ?v=16 in base.html, test in browser.
When done, update T1 status to DONE in planning/EXPANSION_PLAN.md.
```

---

## T2: Explore — Full Egypt Heritage Expansion

### Status: NOT STARTED

### Current State
- 157 entries in `data/expanded_sites.json`
- 50 entries have EMPTY category and region
- 22 entries have no images
- 36 entries have no coordinates
- Duplicates: abu_simbel has empty fields, aswan_dam/aswan_high_dam, pompey_pillar/pompeys_pillar, catacombs_kom_el_shoqafa/catacombs_of_kom_el_shoqafa, egyptian_museum/egyptian_museum_cairo, great_pyramid_of_giza/great_pyramids_of_giza
- Non-landmarks: akhenaten, amenhotep_iii, king_thutmose_iii, ramesses_ii, nefertiti_bust, statue_of_tutankhamun, mask_of_tutankhamun (these are pharaohs/artifacts, not places)
- Only 20 have rich curated data (ATTRACTIONS dict in landmarks.py)
- Only 55/157 have local image metadata files
- Arabic extracts exist in text/*.json but are NOT used

### Architecture Design

#### New Category Structure (Hierarchical)

```
Egyptian Heritage
├── Pharaonic & Ancient Egyptian
│   ├── Pyramids & Necropolises
│   │   ├── Great Pyramids of Giza (Khufu, Khafre, Menkaure)
│   │   ├── Step Pyramid of Djoser (Saqqara)
│   │   ├── Bent Pyramid & Red Pyramid (Dahshur)
│   │   ├── Abu Rawash
│   │   ├── Meidum Pyramid
│   │   └── Pyramid of Hawara
│   ├── Temples
│   │   ├── Karnak Temple Complex (multiple precincts)
│   │   ├── Luxor Temple
│   │   ├── Abu Simbel (Ramesses II + Nefertari)
│   │   ├── Temple of Hatshepsut (Deir el-Bahari)
│   │   ├── Dendera Temple Complex (Hathor)
│   │   ├── Edfu Temple (Horus)
│   │   ├── Kom Ombo Temple (Sobek & Haroeris)
│   │   ├── Philae Temple (Isis) — Agilkia Island
│   │   ├── Abydos Temple (Seti I)
│   │   ├── Medinet Habu (Ramesses III)
│   │   ├── Esna Temple (Khnum)
│   │   ├── Kalabsha Temple
│   │   └── Temple of Hibis (Kharga)
│   ├── Tombs & Valleys
│   │   ├── Valley of the Kings (62+ tombs)
│   │   ├── Valley of the Queens
│   │   ├── Tombs of the Nobles
│   │   ├── Workers' Village (Deir el-Medina)
│   │   └── Beni Hasan Tombs
│   ├── Monuments & Statues
│   │   ├── Great Sphinx of Giza
│   │   ├── Colossi of Memnon
│   │   ├── Unfinished Obelisk (Aswan)
│   │   ├── Memphis Open Air Museum (Ramesses II statue)
│   │   └── Cleopatra's Needle (context: original locations)
│   └── Ancient Cities & Sites
│       ├── Memphis (first capital)
│       ├── Thebes / Luxor
│       ├── Amarna (Akhenaten's capital)
│       ├── Tanis (Biblical Zoan)
│       └── Elephantine Island
│
├── Greco-Roman
│   ├── Bibliotheca Alexandrina (modern, on site of ancient Library)
│   ├── Catacombs of Kom el-Shoqafa
│   ├── Pompey's Pillar
│   ├── Roman Theater (Alexandria)
│   ├── Temple of Augustus (Philae area)
│   └── Antinopolis ruins
│
├── Coptic & Early Christian
│   ├── Hanging Church (Al-Muallaqah)
│   ├── Church of St. Sergius & Bacchus (Abu Serga)
│   ├── Coptic Museum
│   ├── St. Catherine's Monastery (Sinai)
│   ├── Wadi El Natrun Monasteries
│   ├── Red Monastery & White Monastery (Sohag)
│   ├── Monastery of St. Anthony
│   └── Monastery of St. Paul
│
├── Islamic Heritage
│   ├── Historic Cairo (UNESCO)
│   │   ├── Al-Muizz Street
│   │   ├── Khan El-Khalili Bazaar
│   │   ├── Bab Zuweila
│   │   ├── Bab al-Futuh & Bab al-Nasr
│   │   └── Bayt al-Suhaymi (Ottoman House)
│   ├── Mosques
│   │   ├── Al-Azhar Mosque (970 AD, Fatimid)
│   │   ├── Mosque of Muhammad Ali (Citadel)
│   │   ├── Sultan Hassan Mosque-Madrasa
│   │   ├── Al-Rifa'i Mosque
│   │   ├── Ibn Tulun Mosque (879 AD, oldest intact)
│   │   ├── Al-Hakim Mosque
│   │   ├── Al-Hussein Mosque
│   │   ├── Amr ibn al-As Mosque (first in Africa, 642 AD)
│   │   └── Qalawun Complex
│   ├── Citadels & Fortresses
│   │   ├── Saladin Citadel (Cairo)
│   │   ├── Qaitbay Citadel (Alexandria)
│   │   └── Shali Fortress (Siwa)
│   └── Madrasas & Mausoleums
│       ├── City of the Dead (Cairo Necropolis)
│       └── Madrasa of Sultan Barquq
│
├── Museums
│   ├── Grand Egyptian Museum (GEM) — Giza (2024)
│   │   ├── Main Halls
│   │   ├── Tutankhamun Collection (5,000+ artifacts)
│   │   ├── Royal Mummy Hall
│   │   ├── Solar Boat Museum (Khufu)
│   │   └── Grand Staircase (87 royal statues)
│   ├── Egyptian Museum (Tahrir Square)
│   │   ├── Royal Mummies Room
│   │   ├── Tutankhamun treasures (partial)
│   │   └── Amarna collection
│   ├── National Museum of Egyptian Civilization (NMEC) — Fustat
│   │   └── Royal Mummies Hall (22 mummies)
│   ├── Luxor Museum
│   ├── Nubia Museum (Aswan)
│   ├── Alexandria National Museum
│   ├── Coptic Museum (Old Cairo)
│   ├── Museum of Islamic Art (Cairo)
│   ├── Graeco-Roman Museum (Alexandria)
│   └── Imhotep Museum (Saqqara)
│
├── Natural Wonders
│   ├── Nile River
│   │   ├── Nile Valley overview
│   │   ├── Nile Cruise (Luxor-Aswan)
│   │   ├── Lake Nasser
│   │   ├── Aswan (First Cataract area)
│   │   └── Nile Delta
│   ├── Deserts
│   │   ├── White Desert (Farafra)
│   │   ├── Black Desert
│   │   ├── Crystal Mountain
│   │   ├── Great Sand Sea
│   │   └── Western Desert overview
│   ├── Oases
│   │   ├── Siwa Oasis
│   │   ├── Bahariya Oasis
│   │   ├── Farafra Oasis
│   │   ├── Dakhla Oasis
│   │   └── Kharga Oasis
│   ├── Coastal & Marine
│   │   ├── Red Sea Coral Reefs
│   │   ├── Ras Mohammed National Park
│   │   ├── Blue Hole (Dahab)
│   │   ├── Tiran Island
│   │   └── Wadi El Gemal National Park
│   └── Mountains & Geological
│       ├── Mount Sinai (Jabal Musa)
│       ├── St. Catherine peaks
│       ├── Colored Canyon (Sinai)
│       └── Wadi Degla Protected Area
│
├── Modern & Contemporary
│   ├── Cairo Tower
│   ├── Aswan High Dam
│   ├── Suez Canal
│   ├── Opera House (Cairo)
│   ├── Baron Empain Palace (Heliopolis)
│   ├── Abdeen Palace
│   ├── Manial Palace
│   └── Alexandria Corniche
│
└── Resort & Beach
    ├── Sharm El Sheikh
    ├── Hurghada
    ├── El Gouna
    ├── Marsa Alam
    ├── Dahab
    ├── Ain Sokhna
    ├── North Coast (Sahel)
    └── Nuweiba
```

### Per-Site Data Requirements

Each site/place MUST have:
```json
{
  "slug": "karnak_temple",
  "name": "Karnak Temple Complex",
  "name_ar": "معبد الكرنك",
  "category": "Pharaonic",
  "subcategory": "Temples",
  "region": "Luxor",
  "period": "Middle Kingdom to Ptolemaic",
  "description": "250+ words English description",
  "description_ar": "Arabic description (from Wikipedia AR or generated)",
  "highlights": ["list", "of", "key", "features"],
  "visiting_tips": ["opening hours", "best time", "ticket info"],
  "historical_significance": "Why this matters",
  "coordinates": {"lat": 25.7188, "lng": 32.6573},
  "images": [
    {"url": "...", "caption": "Hypostyle Hall", "source": "Wikipedia/Unsplash"},
    {"url": "...", "caption": "Sacred Lake", "source": "..."}
  ],
  "related_sites": ["luxor_temple", "valley_of_the_kings"],
  "parent_site": null,
  "child_sites": ["karnak_precinct_amun", "karnak_precinct_mut"],
  "tags": ["UNESCO", "must-visit", "photography"],
  "notable_features": {},
  "has_sub_sections": true
}
```

### Changes Needed

1. **Data layer** (`data/expanded_sites.json` → full rewrite):
   - Deduplicate (merge pairs)
   - Separate pharaohs/artifacts → they become content WITHIN museum pages (e.g., Tutankhamun's mask → inside GEM page)
   - Fill ALL empty categories and regions
   - Add ~100+ new sites to reach comprehensive coverage
   - Add subcategories
   - Add Arabic names
   - Multiple images per site
   - Parent/child relationships (e.g., GEM → Tutankhamun Gallery)

2. **Core layer** (`app/core/landmarks.py`):
   - Update ATTRACTIONS to match new schema
   - Add subcategory field
   - Support parent/child site relationships
   - Load enriched data from JSON (reduce hardcoded data)

3. **API layer** (`app/api/explore.py`):
   - Support hierarchical browsing (category → subcategory → site → sub-sections)
   - Filter by region
   - Support Arabic descriptions
   - Return related sites
   - Better image handling

4. **Template** (`app/templates/explore.html`):
   - Category sidebar/tabs with subcategories
   - Detail view with image gallery (multiple images)
   - "Inside this site" section for large complexes
   - Related sites navigation
   - Better mobile UX

### Data Sources (Online)
- Wikipedia EN/AR: descriptions, coordinates, images (already have 157 text/*.json files)
- Wikimedia Commons: high-quality CC-licensed images
- UNESCO World Heritage: https://whc.unesco.org/en/statesparties/eg (7 sites)
- Google Maps: coordinates verification
- Ministry of Tourism: https://en.egypt.travel/
- Lonely Planet: editorial descriptions (for reference only, don't copy)

### Target Count: ~250+ unique heritage sites/places

### Detailed Implementation Steps

#### Step 1: Fix expanded_sites.json data
- Open `data/expanded_sites.json` (157 entries currently)
- **Deduplicate** these pairs (merge into best entry):
  - `abu_simbel` (empty) + proper Abu Simbel entry
  - `aswan_dam` / `aswan_high_dam` → keep `aswan_high_dam`
  - `pompey_pillar` / `pompeys_pillar` → keep `pompeys_pillar`
  - `catacombs_kom_el_shoqafa` / `catacombs_of_kom_el_shoqafa` → keep shorter slug
  - `egyptian_museum` / `egyptian_museum_cairo` → keep `egyptian_museum`
  - `great_pyramid_of_giza` / `great_pyramids_of_giza` → keep `great_pyramids_of_giza`
- **Remove non-places** (pharaohs/artifacts — absorb their content into parent sites):
  - `akhenaten` → content goes to `amarna` / Karnak
  - `amenhotep_iii` → content goes to Luxor Temple / Colossi of Memnon
  - `king_thutmose_iii` → content goes to Karnak / Valley of the Kings
  - `ramesses_ii` → content goes to Abu Simbel / Memphis
  - `nefertiti_bust` → content goes to `grand_egyptian_museum`
  - `statue_of_tutankhamun` / `mask_of_tutankhamun` → content goes to GEM
- **Fill 50 empty categories** using this mapping:
  - Ancient/Pharaonic sites → `"category": "Pharaonic"` + appropriate subcategory
  - Mosques → `"category": "Islamic"`, subcategory `"Mosques"`
  - Churches → `"category": "Coptic"`, subcategory `"Churches"`
  - Natural → `"category": "Natural"`, subcategory based on type
- **Add ALL missing sites** from the Category Tree above (~100 new entries)
- Each entry follows the Per-Site Data schema above

#### Step 2: Update landmarks.py Pydantic model (`app/core/landmarks.py`)
- Current file: ~860 lines, has `AttractionType(StrEnum)` with 4 types, `Attraction(BaseModel)` Pydantic model
- Add new fields to `Attraction`:
  - `subcategory: str = ""`
  - `name_ar: str = ""`
  - `parent_slug: str | None = None`
  - `child_slugs: list[str] = []`
  - `related_slugs: list[str] = []`
  - `period: str = ""`
  - `highlights: list[str] = []`
- Update `AttractionType` to include: `PHARAONIC`, `GRECO_ROMAN`, `COPTIC`, `ISLAMIC`, `MUSEUM`, `NATURAL`, `MODERN`, `RESORT`
- Keep the 20 curated ATTRACTIONS but update their fields to match new schema

#### Step 3: Update explore.py API (`app/api/explore.py`)
- Current: 2 routers (`/api/landmarks` + `/api/explore`), ~530 lines
- Key functions: `_load_wiki_data()`, `_load_model_classes()`, 3-tier lookup
- Add new endpoints:
  - `GET /api/explore/categories` — returns category→subcategory tree
  - `GET /api/explore/browse?category=X&subcategory=Y` — filtered list
  - `GET /api/explore/site/{slug}/related` — related sites
  - `GET /api/explore/site/{slug}/children` — sub-sections
- Update existing `GET /api/landmarks` to include new fields
- Ensure Arabic text support (`description_ar`, `name_ar`)

#### Step 4: Update explore.html UI (`app/templates/explore.html`)
- Current: ~600 lines, Alpine `exploreApp()`, mode tabs (Browse All / Identify)
- Add:
  - Category sidebar with collapsible subcategories (accordion)
  - "Region" filter dropdown (Cairo, Luxor, Aswan, Alexandria, Sinai, etc.)
  - Detail modal: image carousel (multiple images per site)
  - "Inside this site" section for sites with `child_slugs`
  - "Related Sites" cards row in detail view
  - Arabic toggle button (show Arabic name/description)
  - Better mobile: bottom sheet for detail on mobile

#### After T2 is complete:
```bash
cd "D:\Personal attachements\Projects\Final_Horus\Wadjet-v2"
npm run build
# Bump cache version in base.html: ?v=17 → ?v=18
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Test: http://localhost:8000/explore
# Verify: categories load, subcategories expand, image galleries work, Arabic text shows
```

### T2 Self-Prompt (copy this when starting T2)
```
I'm working on Wadjet v2, Task T2: Full Egypt Heritage Explore Expansion.
Read planning/EXPANSION_PLAN.md for the full plan.

This is the LARGEST task — it rewrites the Explore section comprehensively.

Files to modify (in order):
1. data/expanded_sites.json — REWRITE: deduplicate, remove non-places, fill categories,
   add ~100 new sites, add subcategories/Arabic/coordinates/images per schema
2. app/core/landmarks.py — Update Attraction model: add subcategory, name_ar, parent_slug,
   child_slugs, period, highlights. Update AttractionType enum.
3. app/api/explore.py — Add category tree endpoint, subcategory browse, related/children
   endpoints. Support Arabic fields.
4. app/templates/explore.html — Add category sidebar with accordion subcategories,
   region filter, image carousel in detail, "Inside this site" section, Arabic toggle.

Key data:
- Current: 157 entries, 50 empty categories, 22 no images, 36 no coords
- Target: 250+ sites, full hierarchy, all fields populated
- Category tree: Pharaonic, Greco-Roman, Coptic, Islamic, Museums, Natural, Modern, Resort
- Each site needs: slug, name, name_ar, category, subcategory, region, period,
  description (250+ words), coordinates, images[], related_sites[]

After changes: npm run build, bump cache version, test all explore routes.
When done, update T2 status to DONE in planning/EXPANSION_PLAN.md.
```

---

## T2.2: Explore — Deep Content, Images & Complete Coverage

### Status: DONE ✅

### Final Results
| Metric | Before T2.2 | After T2.2 |
|--------|-------------|------------|
| Total sites | 194 | **260** (+66) |
| Top-level sites | 140 | **161** (+21) |
| Children | 54 | **99** (+45) |
| Parent sites with children | 14 | **25** (+11) |
| Sites with images | 1 | **260** (100%) |
| Sites with multiple images (2-6) | 0 | **260** (100%) |
| Total images across all sites | 0 | **1,220** |
| Featured sites | 49 | **76** |
| Categories | 8 | 8 (Pharaonic 105, Islamic 36, Museum 34, Natural 26, Modern 22, Coptic 19, Greco-Roman 10, Resort 8) |

Image distribution: 7 sites with 2 imgs, 6 with 3, 107 with 4, 80 with 5, 60 with 6.

### What Was Done

**Phase A (Session 1):**
1. **GEM Updated** — Corrected to "Inaugurated November 2025", real Wikipedia descriptions, 10 children with real gallery data
2. **11 new parent sites got children** — Cairo Citadel (6), Hatshepsut (5), Philae (4), Dendera (4), Edfu (3), Kom Ombo (3), NMEC (3), Bibliotheca (4), Khan El Khalili (2), Abydos (3), St. Catherine's (4)
3. **Image population** — `populate_images.py` + `_fix_missing_images.py` + `_add_manual_images.py` → 243/243 sites with at least 1 image
4. **Multi-image fetch** — `_fetch_multi_images.py` got 5-6 images from Wikipedia for 29 major sites
5. **New sites added** — Blue Hole Dahab, Cairo Opera House, El Gouna, Marsa Alam
6. **New files**: `citadel_sections.py`, `hatshepsut_sections.py`, `temple_sections.py`, `cultural_sections.py`, `populate_images.py`

**Phase B (Session 2 — Completeness Audit):**
7. **Gap analysis** — Checked 40 must-have Egyptian tourist sites, found 14 missing (9 truly new after alias resolution)
8. **17 new sites added** across 7 files:
   - `museums.py`: +mummification_museum, +solar_boat_museum
   - `modern.py`: +new_administrative_capital, +port_said, +ismailia
   - `natural.py`: +ain_sukhna, +wadi_degla
   - `pharaonic_monuments.py`: +aga_khan_mausoleum, +tombs_of_the_nobles_aswan
   - `greco_roman.py`: +ras_el_tin_palace, +abu_mena
   - NEW `experiences.py`: +nile_cruise, +hot_air_balloon_luxor, +sound_and_light_pyramids, +sound_and_light_karnak, +nubian_village, +felucca_ride_aswan
9. **100% multi-image coverage** — 3-tier image pipeline:
   - `_fetch_multi_images.py` (Wikipedia page images API) → 127 top-level + 99 children updated
   - `_fetch_commons_images.py` (Wikimedia Commons search API fallback) → 34 remaining sites updated
   - Result: **260/260 sites have 2-6 images (100%)**
10. **V1 project checked** — `attractions_data.py` has 20 curated attractions with rich fields, already integrated at runtime via `get_by_slug()` in explore.py
11. **Repos folder checked** — ~100+ repos in D:\Personal attachements\Repos\, none Egypt/tourism related

### Goals
1. **Images for EVERY site** — populate images[] from wiki data (119 auto-match) + manual for rest
2. **Deep nesting** — add children for 15+ more major parent sites
3. **Update GEM** — officially opened Nov 1, 2025 (not 2024); add real gallery data from Wiki research
4. **Add missing major sites** — complete Egypt coverage
5. **Rich sections** — more sites should have detailed section content

### Phase 1: Populate Images from Wiki Data (119 sites)
**Script**: `scripts/populate_images.py`
- Read all `data/text/*.json` → extract `wikipedia.en.thumbnail` and `wikipedia.en.original_image`
- Match by slug to expanded_sites.json
- Set `images: [{"url": original_image, "caption": site_name, "source": "Wikimedia Commons"}]`
- For children without wiki data, use parent's wiki image with child-specific caption
- **Target**: 119+ sites get at least 1 image automatically

### Phase 2: Update GEM with Real 2025 Data
**Source**: Wikipedia research (completed)
- Update GEM period: "Opened 2024" → "Inaugurated November 2025"
- Update GEM description with accurate $1.2B cost, 100,000+ artifacts, official opening details
- Update GEM children with accurate data from Wikipedia:
  - **Grand Hall (Atrium)**: 10,000 m², glass roof, Ramesses II colossus (11m, 83t), 20-30 large artifacts
  - **Grand Staircase**: 6,000 m², 6 stories, 60+ artifacts in 4 thematic sections (Royal Image, Divine Houses, Gods & Kings, Funerary)
  - **Tutankhamun Halls**: 2 halls, 7,000 m², 5,398 artifacts — first time complete collection displayed together
  - **Khufu Ships Museum**: 2 solar boats, 4,600 years old, transferred from Giza in 2021
  - **Children's Museum**: Interactive, 5,000 m², ages 6-12, AR experiences
  - **Main Galleries**: 12 halls by time period (Halls 1-3: Prehistoric/Old Kingdom, 4-6: Middle Kingdom, 7-9: New Kingdom, 10-12: Late Period/Greco-Roman)
  - ADD: **Conservation Center** — 19 labs, largest restoration center in Middle East
  - ADD: **Temporary Exhibition Halls** — 4 halls, 5,000 m²
  - ADD: **Conference Center** — 40,000 m², 1,000-seat auditorium, 250-seat 3D theater

### Phase 3: Add Children for Major Parent Sites
New section files to create:

| Parent Site | Children to Add | File |
|-------------|----------------|------|
| Cairo Citadel | Mosque of Muhammad Ali, Military Museum, Police Museum, Gawhara Palace, Al-Nasir Muhammad Mosque, Sulayman Pasha Mosque | `citadel_sections.py` |
| Hatshepsut Temple | Lower Terrace, Middle Terrace, Upper Terrace, Hathor Chapel, Anubis Chapel, Mortuary Complex | `hatshepsut_sections.py` |
| Dendera Temple | Hypostyle Hall, Zodiac Chapel, Crypts, Sacred Lake, Birth House (Mammisi), Roof Chapels | `dendera_sections.py` |
| Philae Temple | Temple of Isis, Kiosk of Trajan, Temple of Hathor, Hadrian's Gate, Second Pylon | `philae_sections.py` |
| Edfu Temple | Great Pylon, Court of Offerings, Hypostyle Halls, Sanctuary/Holy of Holies, Enclosure Wall | `edfu_sections.py` |
| Kom Ombo | Temple of Sobek, Temple of Horus the Elder, Nilometer, Crocodile Museum | `kom_ombo_sections.py` |
| NMEC | Royal Mummies Hall, Main Exhibition, Textile Gallery, Fustat Garden | `nmec_sections.py` |
| Bibliotheca Alexandrina | Main Library Hall, Planetarium, Antiquities Museum, Manuscripts Museum, Culturama | `bibliotheca_sections.py` |
| Khan El Khalili | Historic Bazaar, Al-Fishawi Coffee House, Gold & Spice Souqs | `khan_el_khalili_sections.py` |
| Abydos Temple | King List Hall, Osireion, Seven Chapels, Hypostyle Halls | `abydos_sections.py` |
| St. Catherine's Monastery | Basilica of Transfiguration, Burning Bush Chapel, Library, Charnel House, Moses' Well | `st_catherine_sections.py` |

### Phase 4: Add Missing Major Sites
Sites Egypt is known for that we might be missing:
- Check for: Medinet Habu, Ramesseum, Colossi of Memnon, Valley of the Queens, Deir el-Medina
- Check for: Esna Temple, Temple of Khnum
- Check for: Ain Sukhna, El Gouna, Marsa Alam
- Check for: Wadi El Rayan, Wadi Hitan (Whale Valley), Lake Qarun
- Check for: Cairo Opera House, Egyptian Museum of Modern Art
- Check for: Montazah Palace & Gardens, Ras el-Tin Palace

### Phase 5: Enrich Thin Content
- Add sections[] to all sites that currently only have description (no section detail)
- Improve descriptions for any still-thin sites

### Execution Order
1. ✅ Audit & research (done)
2. Write T2.2 plan (this section)
3. Update GEM data with real 2025 info
4. Create image population script → run it
5. Create new section files for 11 parent sites
6. Add any missing major sites
7. Rebuild expanded_sites.json
8. Test API endpoints
9. Verify in browser

---

## T3: Dictionary — Complete Gardiner Sign List

### Status: DONE ✅

### Completed (Session 20-21)
- **1023 signs** across 26 categories (was 177) — using Unicode block U+13000-U+1342E
- Created `app/core/gardiner_data/` package with 26 per-category Python files + `__init__.py`
- Generation script: `scripts/build_gardiner_data.py` with curated descriptions, phonetics, logographic values
- Refactored `app/core/gardiner.py` as backward-compatible facade (~200 lines, was ~580)
- `_PRIMARY_UNILITERALS` ensures 25 canonical uniliterals win in write.py iteration order
- API: pagination (`?page=&per_page=`), `/alphabet` (25 uniliterals), `/lesson/{1-5}` (5 levels)
- UI: Browse/Learn tabs, pagination with smart page numbers, lesson cards with descriptions
- All 11 endpoint tests pass, dictionary HTML renders correctly
- Cache bumped to v17

### Current State
- 177 signs defined in `app/core/gardiner.py`
- Only UNILITERALS (~25) and BILITERALS (~152) dicts exist
- No separate TRILITERALS, LOGOGRAMS, DETERMINATIVES, NUMBERS dicts
- 6 sign types distinguished but scattered across BILITERALS
- Unicode coverage: ~135 signs have unicode_char
- No images — relies entirely on Unicode font rendering
- No example words/usage
- No pronunciation guide beyond MdC notation
- Dictionary UI is basic: category filter + search + modal detail

### Full Gardiner Sign List (from Wikipedia research)

| Category | Name | Expected # Signs | Currently Have |
|----------|------|-----------------|----------------|
| A | Man and his occupations | 60 | ~6 |
| B | Woman and her occupations | 12 | ~2 |
| C | Anthropomorphic deities | 20 | ~2 |
| D | Parts of human body | 70 | ~20 |
| E | Mammals | 40 | ~8 |
| F | Parts of mammals | 60 | ~12 |
| G | Birds | 60 | ~18 |
| H | Parts of birds | 10 | ~3 |
| I | Amphibious animals, reptiles | 15 | ~4 |
| K | Fish | 10 | ~2 |
| L | Invertebrates | 10 | ~3 |
| M | Trees and plants | 44 | ~12 |
| N | Sky, earth, water | 42 | ~16 |
| O | Buildings | 51 | ~6 |
| P | Ships | 20 | ~4 |
| Q | Domestics/funerary | 10 | ~2 |
| R | Temple furniture | 30 | ~6 |
| S | Crowns, dress, staves | 50 | ~6 |
| T | Warfare, hunting | 40 | ~5 |
| U | Agriculture, crafts | 41 | ~6 |
| V | Rope, fiber, baskets | 40 | ~8 |
| W | Vessels | 25 | ~6 |
| X | Loaves and cakes | 8 | ~3 |
| Y | Writings, games, music | 8 | ~3 |
| Z | Strokes | 11 | ~3 |
| Aa | Unclassified | 50+ | ~6 |
| **TOTAL** | | **~750+** | **~177** |

### Changes Needed

1. **gardiner.py — MASSIVE expansion**:
   - Add ALL ~750+ Gardiner signs (A1-A60, B1-B12, C1-C20, D1-D70, E1-E40, F1-F60, G1-G60, H1-H10, I1-I15, K1-K10, L1-L10, M1-M44, N1-N42, O1-O51, P1-P20, Q1-Q10, R1-R30, S1-S50, T1-T40, U1-U41, V1-V40, W1-W25, X1-X8, Y1-Y8, Z1-Z11, Aa1-Aa50)
   - Each sign needs: code, transliteration, type, description, category, phonetic_value, unicode_char
   - Map Unicode code points from Egyptian Hieroglyphs block (U+13000–U+1342F)
   - Add example_words field showing common words using each sign
   - Add `is_classifier_class: bool` flag for signs our ML model can detect
   - Split into separate dicts by type for clarity or use a single large dict
   - **Data source**: Wikipedia List of Egyptian hieroglyphs + Gardiner's Egyptian Grammar (public domain reference)

2. **dictionary.py (API)**:
   - Add pagination (750+ signs is too many at once)
   - Add `type` filter (show me all uniliterals, all determinatives, etc.)
   - Add "educational mode" endpoint — returns lesson-style content
   - Add "word examples" endpoint — given a sign, show words using it
   - Add `is_in_classifier` field to distinguish signs we can ML-detect vs. reference-only

3. **dictionary.html (Template)**:
   - **Educational flow**: Start with "The Egyptian Alphabet" (26 uniliterals) → biliterals → triliterals → logograms → determinatives
   - "Lesson" mode: step-by-step introduction
   - Improved sign cards: larger glyph, pronunciation, example words
   - Category accordion/tree navigation (A. Man → A1 sitting man, A2 man with hand to mouth...)
   - Highlight "in our scanner" signs differently (gold border = our AI can detect this)
   - Reading direction guide (right-to-left rules, how to determine direction)
   - "Build a word" interactive tool using the dictionary signs
   - Mobile-optimized grid

### Unicode Mapping Reference
- Egyptian Hieroglyphs Unicode block: U+13000 to U+1342F (1,071 characters)
- Extended block A: U+13430 to U+1345F (Egyptian Hieroglyph Format Characters)
- Extended block B: U+13460 to U+143FF
- Standard Gardiner mapping: A001 → U+13000, A002 → U+13001, etc.
- Font requirement: Noto Sans Egyptian Hieroglyphs (already loaded in base.html)

### Online References
- Wikipedia: https://en.wikipedia.org/wiki/Gardiner%27s_sign_list (complete sign grid)
- Wikipedia: https://en.wikipedia.org/wiki/List_of_Egyptian_hieroglyphs (detailed per-sign data)
- JSesh sign database: comprehensive Egyptological reference
- Thot Sign List: https://thotsignlist.org/ (interactive database)
- Unicode charts: https://www.unicode.org/charts/PDF/U13000.pdf

### Detailed Implementation Steps

#### Step 1: Architect the new gardiner.py structure

Current file (`app/core/gardiner.py`, ~575 lines) has:
- `SignType(Enum)` with 7 values: UNILITERAL, BILITERAL, TRILITERAL, LOGOGRAM, DETERMINATIVE, NUMBER, CLASSIFIER_ONLY
- `GardinerSign` dataclass with 10 fields: code, transliteration, type, description, category, phonetic_value, unicode_char, unicode_hex, is_in_classifier, order
- `UNILITERALS` dict (~26 entries)
- `BILITERALS` dict (~152 entries, mixed types)
- `GARDINER_TRANSLITERATION` merged dict
- `_GARDINER_UNICODE` dict (~120 Unicode mappings)
- Backfill loop that sets unicode from _GARDINER_UNICODE
- `DETERMINATIVE_CATEGORIES` (16 groups)

**New structure** (split into multiple files for 750+ signs):
```
app/core/
  gardiner.py          → Keep as facade: imports, indexes, lookups
  gardiner_data/
    __init__.py
    a_man.py           → A1-A70 (man and his occupations)
    b_woman.py         → B1-B9
    c_deities.py       → C1-C24
    d_body.py          → D1-D67
    e_mammals.py       → E1-E38
    f_parts_mammals.py → F1-F53
    g_birds.py         → G1-G54
    h_parts_birds.py   → H1-H8
    i_reptiles.py      → I1-I15
    k_fish.py          → K1-K8
    l_invertebrates.py → L1-L8
    m_plants.py        → M1-M44
    n_sky_earth.py     → N1-N42 (including NL and NU nomes)
    o_buildings.py     → O1-O51
    p_ships.py         → P1-P11
    q_furniture.py     → Q1-Q7
    r_temple.py        → R1-R29
    s_crowns.py        → S1-S46
    t_warfare.py       → T1-T36
    u_agriculture.py   → U1-U42
    v_rope.py          → V1-V40
    w_vessels.py       → W1-W25
    x_loaves.py        → X1-X8
    y_writings.py      → Y1-Y8
    z_strokes.py       → Z1-Z16H
    aa_unclassified.py → Aa1-Aa32
```

Each data file exports a list of dicts:
```python
# Example: a_man.py
SIGNS_A = [
    {"code": "A1", "unicode": "𓀀", "unicode_hex": "U+13000",
     "description": "seated man", "transliteration": "",
     "phonetic_value": "",
     "sign_type": "DETERMINATIVE",
     "meanings": "I, me, my (masculine)",
     "notes": "Determinative for masculine names"},
    {"code": "A2", "unicode": "𓀁", "unicode_hex": "U+13001",
     "description": "man with hand to mouth", "transliteration": "",
     "phonetic_value": "",
     "sign_type": "DETERMINATIVE",
     "meanings": "eat, drink, speak, think, be silent, plan, love",
     "notes": "Determinative for activities involving the mouth, head, or ideas"},
    # ... all A signs
]
```

Then `gardiner.py` aggregates:
```python
from app.core.gardiner_data import (
    a_man, b_woman, c_deities, d_body, ...
)
ALL_SIGNS: list[GardinerSign] = []
for module in [a_man, b_woman, ...]:
    for entry in module.SIGNS_X:
        ALL_SIGNS.append(GardinerSign(**entry))

SIGN_INDEX = {s.code: s for s in ALL_SIGNS}
```

#### Step 2: Build the sign data files

Use the Wikipedia reference data (fetched and stored in this plan). For EACH sign:

**Complete Wikipedia Gardiner Sign Reference (A through Aa)**

Below is the COMPLETE mapping of Gardiner codes → Unicode chars → descriptions → phonetic values.
Use this as the PRIMARY data source for building the gardiner_data/ files.

**Category A: Man and his occupations (A1-A70)**
| Code | Unicode | Hex | Description | Phonetic | Meanings |
|------|---------|-----|-------------|----------|----------|
| A1 | 𓀀 | U+13000 | seated man | | I, me, my (masculine); det. for masculine names |
| A2 | 𓀁 | U+13001 | man with hand to mouth | | eat, drink, speak, think, be silent, plan, love |
| A3 | 𓀂 | U+13002 | man sitting on heel | | sit, besiege, dwell |
| A4 | 𓀃 | U+13003 | seated man with hands raised | | offer, praise, beseech, hide |
| A5 | 𓀄 | U+13004 | crouching man hiding behind wall | | hide; det. concealing, secret |
| A5A | 𓀅 | U+13005 | seated man hiding behind wall | | hide |
| A6 | 𓀆 | U+13006 | seated man under vase with water | | to be clean |
| A6A | 𓀇 | U+13007 | seated man reaching for libation stone | | to be clean |
| A6B | 𓀈 | U+13008 | seated man reaching down under vase | | to be clean |
| A7 | 𓀉 | U+13009 | fatigued man | | to be tired or weak |
| A8 | 𓀊 | U+1300A | man performing hnw-rite | | rejoice, celebrate |
| A9 | 𓀋 | U+1300B | man steadying basket on head | f | work, toil, load, carry |
| A10 | 𓀌 | U+1300C | seated man holding oar | | to saw, rower |
| A11 | 𓀍 | U+1300D | seated man holding scepter and crook | | friend |
| A12 | 𓀎 | U+1300E | soldier with bow and quiver | | soldier, army |
| A13 | 𓀏 | U+1300F | man with arms tied behind back | | enemy, rebel |
| A14 | 𓀐 | U+13010 | falling man with blood | | die, enemy |
| A14A | 𓀑 | U+13011 | man hit with axe | | |
| A15 | 𓀒 | U+13012 | man falling | | trap |
| A16 | 𓀓 | U+13013 | man bowing down | | to bend, bow, do homage |
| A17 | 𓀔 | U+13014 | child with hand to mouth | ms, nn | young, child, orphan, infant |
| A17A | 𓀕 | U+13015 | child with arms hanging | | noble/aristocratic youth |
| A18 | 𓀖 | U+13016 | child wearing red crown | | foster child |
| A19 | 𓀗 | U+13017 | bent man leaning on staff | jk | old, fragile, elder, great, wise |
| A20 | 𓀘 | U+13018 | man leaning on forked staff | | elder |
| A21 | 𓀙 | U+13019 | man holding staff with handkerchief | | civil servant, courtier, great |
| A22 | 𓀚 | U+1301A | statue of man with staff and scepter | | statue |
| A23 | 𓀛 | U+1301B | king with staff and mace | | monarch, lord, ruler |
| A24 | 𓀜 | U+1301C | man striking with both hands | | hit, strike, power, strength |
| A25 | 𓀝 | U+1301D | man striking with left arm behind | | hit, strike |
| A26 | 𓀞 | U+1301E | man with one arm pointing | | call |
| A27 | 𓀟 | U+1301F | hastening man | jn | bring |
| A28 | 𓀠 | U+13020 | man with hands raised high | | to be high, elevate, mourn |
| A29 | 𓀡 | U+13021 | man upside down | | headlong |
| A30 | 𓀢 | U+13022 | man with hands raised in front | | praise, adore, thank |
| A31 | 𓀣 | U+13023 | man with hands raised behind | | to turn away |
| A32 | 𓀤 | U+13024 | man dancing, arms to back | | dance, cheer, rejoice |
| A32A | 𓀥 | U+13025 | man dancing, arms to front | | dance |
| A33 | 𓀦 | U+13026 | man with stick and bundle | | shepherd, journey, foreign |
| A34 | 𓀧 | U+13027 | man pounding in mortar | | to stomp, grind |
| A35 | 𓀨 | U+13028 | man building wall | | to build |
| A36 | 𓀩 | U+13029 | man kneading into vessel | | brewer, grind |
| A37 | 𓀪 | U+1302A | man in vessel | | brewer |
| A38 | 𓀫 | U+1302B | man holding necks of two animals | | Cusae |
| A39 | 𓀬 | U+1302C | man on two giraffes | | Cusae |
| A40 | 𓀭 | U+1302D | seated god | | God, det. for god names |
| A40A | 𓀮 | U+1302E | seated god with Was-sceptre | | God |
| A41 | 𓀯 | U+1302F | king with uraeus | | king, majesty |
| A42 | 𓀰 | U+13030 | king with uraeus and flagellum | | king, majesty |
| A42A | 𓀱 | U+13031 | king with uraeus and flagellum | | king, majesty |
| A43 | 𓀲 | U+13032 | king wearing white crown | | King of Upper Egypt, Osiris |
| A43A | 𓀳 | U+13033 | king white crown with sceptre | | King of Upper Egypt, Osiris |
| A44 | 𓀴 | U+13034 | king white crown with flagellum | | King of Upper Egypt, Atum |
| A45 | 𓀵 | U+13035 | king wearing red crown | n | King of Lower Egypt |
| A45A | 𓀶 | U+13036 | king red crown with sceptre | n | Atum |
| A46 | 𓀷 | U+13037 | king red crown with flagellum | | King of Lower Egypt |
| A47 | 𓀸 | U+13038 | shepherd seated in mantle | | shepherd, guard |
| A48 | 𓀹 | U+13039 | beardless man with knife | | belonging to, keeper |
| A49 | 𓀺 | U+1303A | seated Syrian holding stick | | foreigner, Asian |
| A50 | 𓀻 | U+1303B | noble on chair | | courtier, noble |
| A51 | 𓀼 | U+1303C | noble on chair with flagellum | | to be noble |
| A52 | 𓀽 | U+1303D | noble squatting with flagellum | | to be noble |
| A53 | 𓀾 | U+1303E | standing mummy | | image, form, likeness |
| A54 | 𓀿 | U+1303F | lying mummy | | death |
| A55 | 𓁀 | U+13040 | mummy on bed | | lie down, corpse |
| A56 | 𓁁 | U+13041 | seated man holding stick | | |
| A57 | 𓁂 | U+13042 | man holding loaf on mat | | offering formula |
| A58 | 𓁃 | U+13043 | man applying hoe to ground | | |
| A59 | 𓁄 | U+13044 | man threatening with stick | | |
| A60 | 𓁅 | U+13045 | man sowing seeds | | spill, pour |
| A61 | 𓁆 | U+13046 | man looking over shoulder | | |
| A62 | 𓁇 | U+13047 | Asiatic | | |
| A63 | 𓁈 | U+13048 | king on throne holding staff | | |
| A64 | 𓁉 | U+13049 | man on heels holding cup | | |
| A65 | 𓁊 | U+1304A | man in tunic with mace | | |
| A66 | 𓁋 | U+1304B | man holding sistrum | | Ihy, Great God |
| A67 | 𓁌 | U+1304C | dwarf | | |
| A68 | 𓁍 | U+1304D | man holding up knife | | black eye paint |
| A69 | 𓁎 | U+1304E | seated man with raised right arm | | |
| A70 | 𓁏 | U+1304F | seated man with raised arms | | Heh |

**Category B: Woman and her occupations (B1-B9)**
| Code | Unicode | Hex | Description | Phonetic | Meanings |
|------|---------|-----|-------------|----------|----------|
| B1 | 𓁐 | U+13050 | seated woman | | woman; det. for feminine names |
| B2 | 𓁑 | U+13051 | pregnant woman | | to be pregnant, conceive |
| B3 | 𓁒 | U+13052 | woman giving birth | | to give birth, conceive |
| B4 | 𓁓 | U+13053 | woman giving birth + three skins | | to give birth |
| B5 | 𓁔 | U+13054 | woman suckling child | | to nurse, wet nurse |
| B5A | 𓁕 | U+13055 | woman suckling (simplified) | | |
| B6 | 𓁖 | U+13056 | woman on chair with child | | to nurse |
| B7 | 𓁗 | U+13057 | queen with diadem and flower | | |
| B8 | 𓁘 | U+13058 | woman holding lotus flower | | |
| B9 | 𓁙 | U+13059 | woman holding sistrum | | |

**Category C: Anthropomorphic deities (C1-C24)**
| Code | Unicode | Hex | Description | Phonetic | Meanings |
|------|---------|-----|-------------|----------|----------|
| C1 | 𓁚 | U+1305A | god with sun-disk and uraeus | | Ra |
| C2 | 𓁛 | U+1305B | falcon-headed god with sun-disk + ankh | | Ra |
| C2A | 𓁜 | U+1305C | falcon-headed god with sun-disk | | Ra |
| C2B | 𓁝 | U+1305D | C2A reversed | | Ra |
| C2C | 𓁞 | U+1305E | C2 reversed | | Ra |
| C3 | 𓁟 | U+1305F | god with ibis head | | Thoth |
| C4 | 𓁠 | U+13060 | god with ram head | | Khnum |
| C5 | 𓁡 | U+13061 | god with ram head + ankh | | Khnum |
| C6 | 𓁢 | U+13062 | god with jackal head | | Anubis, Wepwawet |
| C7 | 𓁣 | U+13063 | god with Seth-animal head | | Seth |
| C8 | 𓁤 | U+13064 | ithyphallic god with plumes | | Min |
| C9 | 𓁥 | U+13065 | goddess with horned sun-disk | | Hathor |
| C10 | 𓁦 | U+13066 | goddess with feather | | Maat |
| C10A | 𓁧 | U+13067 | goddess with feather + ankh | | Maat |
| C11 | 𓁨 | U+13068 | god supporting sky | | Heh, million |
| C12 | 𓁩 | U+13069 | god with two plumes + scepter | | Amun |
| C13 | 𓁪 | U+1306A | C12 reversed | | Amun |
| C14 | 𓁫 | U+1306B | god with plumes + scimitar | | Amunherkhepeshef |
| C15 | 𓁬 | U+1306C | C14 reversed | | Amunherkhepeshef |
| C16 | 𓁭 | U+1306D | god wearing red crown + ankh | | Atum |
| C17 | 𓁮 | U+1306E | falcon-headed god + plumes | | Montu |
| C18 | 𓁯 | U+1306F | squatting god | | Tatenen |
| C19 | 𓁰 | U+13070 | mummy-shaped god | | Ptah, divine |
| C20 | 𓁱 | U+13071 | mummy-shaped god in shrine | | Ptah, divine |
| C21 | 𓁲 | U+13072 | Bes | | Bes |
| C22 | 𓁳 | U+13073 | falcon-headed god + moon | | Khonsu |
| C23 | 𓁴 | U+13074 | feline-headed goddess + sun | | Sekhmet, Bastet |
| C24 | 𓁵 | U+13075 | god red crown + scepter | | Atum |

**IMPORTANT NOTE FOR IMPLEMENTATION**:
The complete sign data for categories D through Aa (covering D1-D67, E1-E38, F1-F53, G1-G54, H1-H8, I1-I15, K1-K8, L1-L8, M1-M44, N1-N42, O1-O51, P1-P11, Q1-Q7, R1-R29, S1-S46, T1-T36, U1-U42, V1-V40, W1-W25, X1-X8, Y1-Y8, Z1-Z16H, Aa1-Aa32) has been fully researched from Wikipedia's "List of Egyptian hieroglyphs" page. The Wikipedia data includes:
- Unicode character and hex code for EVERY sign
- Description of what the hieroglyph depicts
- Phonetic values (uniliteral/biliteral/triliteral)
- Meanings and usage context
- Notes on determinative usage

When implementing each category data file, fetch the complete data from:
**https://en.wikipedia.org/wiki/List_of_Egyptian_hieroglyphs**

The Unicode mapping follows a sequential pattern:
- A1=U+13000, A2=U+13001, ... A70=U+1304F
- B1=U+13050, B2=U+13051, ... B9=U+13059
- C1=U+1305A, ... C24=U+13075
- D1=U+13076, ... D67H=U+130D1
- E1=U+130D2, ... E38=U+130FD
- F1=U+130FE, ... F53=U+1313E
- G1=U+1313F, ... G54=U+1317E
- H1=U+1317F, ... H8=U+13187
- I1=U+13188, ... I15=U+1319A
- K1=U+1319B, ... K8=U+131A2
- L1=U+131A3, ... L8=U+131AC
- M1=U+131AD, ... M44=U+131EE
- N1=U+131EF, ... N42=U+1321F (plus NL/NU nomes)
- O1=U+13250, ... O51=U+1329A
- P1=U+1329B, ... P11=U+132A7
- Q1=U+132A8, ... Q7=U+132AE
- R1=U+132AF, ... R29=U+132D0
- S1=U+132D1, ... S46=U+13306
- T1=U+13307, ... T36=U+13332
- U1=U+13333, ... U42=U+13361
- V1=U+13362, ... V40A=U+133AE
- W1=U+133AF, ... W25=U+133CE
- X1=U+133CF, ... X8A=U+133DA
- Y1=U+133DB, ... Y8=U+133E3
- Z1=U+133E4, ... Z16H=U+1340C
- Aa1=U+1340D, ... Aa32=U+1342E

#### Key Uniliteral Signs (The Egyptian Alphabet — 26 signs)
THESE ARE THE MOST IMPORTANT — they form the alphabet:

| Sign | Code | Unicode | Sound | English Equivalent |
|------|------|---------|-------|-------------------|
| 𓄿 | G1 | U+1313F | ꜣ (alef) | glottal stop (like Arabic ا) |
| 𓇋 | M17 | U+131CB | j (yod) | y as in "yes" |
| 𓇌 | M17A | U+131CC | y | y |
| 𓏲 | Z7 | U+133F2 | w | w as in "wet" |
| 𓃀 | D58 | U+130C0 | b | b as in "bed" |
| 𓊪 | Q3 | U+132AA | p | p as in "pen" |
| 𓆑 | I9 | U+13191 | f | f as in "fun" |
| 𓅓 | G17 | U+13153 | m | m as in "man" |
| 𓈖 | N35 | U+13216 | n | n as in "net" |
| 𓂋 | D21 | U+1308B | r | r as in "red" |
| 𓉔 | O4 | U+13254 | h | h as in "hat" |
| 𓎛 | V28 | U+1339B | ḥ | emphatic h |
| 𓐍 | Aa1 | U+1340D | ḫ | ch as in "loch" |
| 𓄡 | F32 | U+13121 | ẖ | soft ch |
| 𓋴 | S29 | U+132F4 | s | s as in "sat" |
| 𓈙 | N37 | U+13219 | š | sh as in "ship" |
| 𓈎 | N29 | U+1320E | q | q (emphatic k) |
| 𓎡 | V31 | U+133A1 | k | k as in "key" |
| 𓎼 | W11 | U+133BC | g | g as in "go" |
| 𓏏 | X1 | U+133CF | t | t as in "top" |
| 𓍿 | V13 | U+1337F | ṯ | ch as in "church" |
| 𓂧 | D46 | U+130A7 | d | d as in "dog" |
| 𓆓 | I10 | U+13193 | ḏ | j as in "judge" |
| 𓂝 | D36 | U+1309D | ꜥ (ayin) | voiced glottal (like Arabic ع) |

#### Step 3: Update dictionary.py API (`app/api/dictionary.py`)
- Current: 145 lines, 3 routes: `GET /categories`, `GET /{code}`, `GET /`
- `CATEGORY_NAMES` dict has 27 entries (A→Aa)
- `_sign_to_dict(sign)` serializes 11 fields

Changes:
- Add pagination: `GET /?page=1&per_page=50` (default 50 per page)
- Add `type` query param: `GET /?sign_type=UNILITERAL`
- Add `GET /alphabet` endpoint — returns just the 26 uniliterals in teaching order
- Add `GET /lesson/{level}` — level 1=alphabet, 2=biliterals, 3=triliterals, 4=all
- Update `_sign_to_dict` to include `meanings`, `notes`, `example_words`

#### Step 4: Update dictionary.html UI (`app/templates/dictionary.html`)
- Current: 273 lines, Alpine `dictionaryApp()`, category pills, sign grid, modal
- State: signs[], categories[], totalSigns, activeCategory, searchQuery, typeFilter, detailSign

Changes:
- Add "Learn" tab that shows educational flow:
  1. "The Egyptian Alphabet" — 26 uniliterals with pronunciation guide
  2. "Common Biliterals" — most frequent two-sound signs
  3. "Triliterals" — three-sound signs
  4. "Logograms" — word-signs
  5. "Determinatives" — meaning classifiers
- Add category tree accordion (click A → see A1, A2... with descriptions)
- Add sign cards with larger Unicode glyph, phonetic value, example words
- Gold border on signs in our ML classifier (is_in_classifier: true)
- "Reading Direction" info panel
- Pagination controls (< 1 2 3 ... >)
- Mobile: full-width cards, swipe for detail

#### After T3 is complete:
```bash
cd "D:\Personal attachements\Projects\Final_Horus\Wadjet-v2"
npm run build
# Bump cache version in base.html: ?v=16 → ?v=17
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Test: http://localhost:8000/dictionary
# Verify: 750+ signs load, categories expand, alphabet lesson works, pagination works
```

### T3 Self-Prompt (copy this when starting T3)
```
I'm working on Wadjet v2, Task T3: Complete Gardiner Sign List Dictionary.
Read planning/EXPANSION_PLAN.md for the full plan — it contains the COMPLETE
Wikipedia reference data for all Gardiner signs (A1-Aa32) with Unicode mappings.

This task expands the dictionary from 177 → 750+ signs.

Files to create/modify:
1. app/core/gardiner_data/ — NEW directory with per-category Python data files
   (a_man.py, b_woman.py, c_deities.py, d_body.py, e_mammals.py, f_parts_mammals.py,
   g_birds.py, h_parts_birds.py, i_reptiles.py, k_fish.py, l_invertebrates.py,
   m_plants.py, n_sky_earth.py, o_buildings.py, p_ships.py, q_furniture.py,
   r_temple.py, s_crowns.py, t_warfare.py, u_agriculture.py, v_rope.py,
   w_vessels.py, x_loaves.py, y_writings.py, z_strokes.py, aa_unclassified.py)
2. app/core/gardiner.py — Refactor to import from gardiner_data/, build ALL_SIGNS index
3. app/api/dictionary.py — Add pagination, type filter, /alphabet, /lesson endpoints
4. app/templates/dictionary.html — Add Learn tab, category accordion, pagination, gold borders

Key data sources:
- Wikipedia: https://en.wikipedia.org/wiki/List_of_Egyptian_hieroglyphs
- Unicode block: U+13000 to U+1342E (sequential mapping per category)
- The plan file has complete A,B,C category data + Unicode ranges for D-Aa

Priority order:
1. Create gardiner_data/ files (A through Aa) — BIGGEST part
2. Refactor gardiner.py to aggregate
3. Update API (pagination, filters)
4. Update UI (learn mode, accordion, pagination)

After changes: npm run build, bump cache version, test /dictionary route.
When done, update T3 status to DONE in planning/EXPANSION_PLAN.md.
```

---

## T3.1: Dictionary — UX Overhaul & Learning Journey

### Status: DONE ✅

### Problem Statement

T3 achieved the data goal (177→1023 signs), but the **user experience is broken for learners**:

1. **~79% of signs show "—" for transliteration** — determinatives are silent (no phonetic value), but the UI shows empty dashes with zero explanation. A user browsing category A (80 signs) sees 76 cards saying "—" and thinks the dictionary is incomplete/broken.

2. **"Transliteration" and "Phonetic Value" are always identical** — both fields in the detail modal pull from the same `phon` data field. When present, user sees the same value twice. When absent, two rows of "—". Either way, it's confusing and wastes space.

3. **No explanation of sign types** — Users encounter badges like "determinative", "logogram", "biliteral" with zero context about what these mean or why some signs have no sound.

4. **Category pills show only letter codes** — "A 80", "K 8", "Aa 34" are meaningless to anyone who doesn't already know the Gardiner system. Users have to click each one to discover what it contains.

5. **Learn tab has no teaching context** — Clicking "Biliterals" shows 69 signs in a grid with a one-sentence description. No explanation of what a biliteral is, how to use it, or how it relates to uniliterals. The user is lost.

6. **No pronunciation guide** — Egyptological transliteration uses special conventions (H = pharyngeal h, X = hard ch, S = sh, D = emphatic d, uppercase ≠ loud). Users see `wDAt` or `xAst` and have no idea how to read them.

7. **Lesson 1 description says "24 signs" but there are 25** — Minor text bug.

8. **"Use in Write →" shown for determinatives** — Clicking this for a silent classifier sign makes no sense.

**Core insight**: المستخدم هيتوه. The dictionary dumps 1023 signs with no narrative, no guidance, no progressive disclosure. We need to transform it from a **data dump** into a **guided learning journey**.

---

### Design Philosophy

The dictionary should serve two audiences simultaneously:
- **Explorers** (Browse tab): Scholars/enthusiasts who know what they want — fast search, category navigation, complete data.
- **Learners** (Learn tab): Complete beginners who need a guided journey — "Teach me hieroglyphs from zero."

The Learn tab becomes a **5-step progressive course** with real teaching content, not just sign grids.

---

### Changes — Backend (dictionary.py + gardiner.py)

#### B1: Smart sign serialization — type-aware fields

**Problem**: The API returns identical `transliteration` and `phonetic_value` for every sign. Determinatives show empty "—" for both.

**Fix** in `_sign_to_dict()`:
- Remove `phonetic_value` field entirely (it's always the same as `transliteration`)
- Add `sound` field: for phonetic signs → the transliteration value; for determinatives/logograms → `null`
- Add `reading` field: a human-friendly label that varies by type:
  - Uniliteral: `"Sounds like 'a' (glottal stop)"` — using a pronunciation guide dict
  - Biliteral: `"Sounds like 'mn'"` — the raw transliteration
  - Triliteral: `"Sounds like 'nfr'"` — the raw transliteration
  - Logogram: `"Means: life; to live"` — from logographic_value
  - Determinative: `"Classifier for: motion, walking"` — from determinative_class, or `"Classifier: [description]"` if no class
  - Number: `"Number sign"` or the actual number value
  - Abbreviation: `"Abbreviation"` 
- Add `fun_fact` field for key signs (~50 most important): short interesting contextual note
  - Example: G1 → "The Egyptian vulture was one of the most common hieroglyphs, appearing in words from names to verbs"
  - Example: S34 → "The ankh (☥) is the most recognized Egyptian symbol worldwide, meaning 'life'"

**New dict in dictionary.py**: `_PRONUNCIATION_GUIDE` mapping ~25 uniliteral sounds to English approximations:
```python
_PRONUNCIATION_GUIDE = {
    "A": ("glottal stop", "like the pause in 'uh-oh'"),
    "i": ("ee", "like 'ee' in 'see'"),
    "y": ("y", "like 'y' in 'yes'"),
    "a": ("ah", "like 'a' in 'father'"),
    "w": ("w/oo", "like 'w' in 'wet' or 'oo' in 'cool'"),
    "b": ("b", "like 'b' in 'boy'"),
    "p": ("p", "like 'p' in 'pet'"),
    "f": ("f", "like 'f' in 'fun'"),
    "m": ("m", "like 'm' in 'mom'"),
    "n": ("n", "like 'n' in 'net'"),
    "r": ("r", "like 'r' in 'run'"),
    "h": ("h", "like 'h' in 'hat'"),
    "H": ("emphatic h", "a forceful 'h' from the throat"),
    "x": ("kh", "like 'ch' in Scottish 'loch'"),
    "X": ("soft kh", "like German 'ich'"),
    "z": ("z", "like 'z' in 'zoo'"),
    "s": ("s", "like 's' in 'sun'"),
    "S": ("sh", "like 'sh' in 'ship'"),
    "q": ("q", "like 'k' but deeper in the throat"),
    "k": ("k", "like 'k' in 'king'"),
    "g": ("g", "like 'g' in 'go'"),
    "t": ("t", "like 't' in 'top'"),
    "T": ("ch", "like 'ch' in 'church'"),
    "d": ("d", "like 'd' in 'dog'"),
    "D": ("j", "like 'j' in 'jump'"),
}
```

#### B2: Lesson API overhaul — real teaching content

**Problem**: Lessons only return a sign list + one-line description. No teaching.

**Fix** — Extend the lesson response with structured educational content:
```json
{
    "level": 1,
    "title": "The Egyptian Alphabet",
    "subtitle": "25 single-consonant signs",
    "description": "...",
    "intro_paragraphs": [
        "Ancient Egyptian hieroglyphs don't have vowels...",
        "These 25 uniliteral signs each represent one consonant sound...",
        "Modern Egyptologists add an 'e' between consonants..."
    ],
    "tip": "Try pronouncing 'nfr' (beautiful) as 'nefer' — add an 'e' between each consonant!",
    "next_lesson": {"level": 2, "title": "Common Biliterals"},
    "signs": [...]
}
```

Lesson content for all 5 levels:

**Lesson 1 — The Egyptian Alphabet (25 uniliterals)**
- Intro: Hieroglyphs don't write vowels, only consonants. These 25 signs each make one sound.
- Tip: Egyptologists add 'e' between consonants for pronunciation (nfr → nefer)
- Key concept: These are the building blocks — every hieroglyphic word uses them.
- Signs shown with pronunciation guide (sound + English approximation)
 
**Lesson 2 — Common Biliterals (69 signs)**
- Intro: Biliterals represent TWO consonants in one sign, making writing more compact.
- Tip: Ancient scribes preferred biliterals over spelling out two separate uniliterals.
- Key concept: When you see a biliteral + one of its consonants repeated = "phonetic complement" (confirmation).
- Example: 𓅓𓈖 = mn + n (the n confirms the ending sound of mn).

**Lesson 3 — Common Triliterals (53 signs)**
- Intro: Triliterals pack three consonants into one powerful sign.
- Tip: Many triliterals depict the very thing they spell (ankh 𓋹 = the word for "life").
- Key concept: Triliterals are often followed by 1-2 phonetic complements to help reading.

**Lesson 4 — Logograms (top 50 with logographic values)**
- Intro: Some signs ARE the word they depict — a house sign means "house" (pr).
- Tip: A single vertical stroke (𓏤) under a sign often marks it as a logogram.
- Key concept: Most logograms can also serve as phonetic signs in other contexts.

**Lesson 5 — Determinatives (top 50 with classes)**
- Intro: Determinatives are SILENT — they appear at the end of a word to classify its meaning.
- Tip: Think of determinatives as "category tags". Walking legs 𓂻 after a verb = motion.
- Key concept: Without determinatives, many words that share the same consonants would be ambiguous.
- This is the "aha moment" — now users understand why 79% of signs have no phonetic value.

#### B3: Fix lesson 1 description ("24" → "25")

One-line fix in `dictionary.py`.

#### B4: Category names in API

Already returned as `category_name` in sign dict. No backend change needed — frontend fix only.

---

### Changes — Frontend (dictionary.html)

#### F1: Browse tab — smarter sign cards

**Current**: Every card shows `sign.transliteration || '—'` — useless for determinatives.

**New card layout** (type-aware):
- **Phonetic signs** (uni/bi/triliteral): Show the transliteration prominently in gold
- **Logograms**: Show `"= meaning"` in green (e.g., `"= life"`)
- **Determinatives**: Show a small tag icon + `"classifier"` in orange instead of "—"
- **Numbers**: Show the number value

This way, every card has meaningful content — no more "—" deserts.

**Category pills** — show category name on hover (tooltip) + show name for wider screens:
- Mobile: `"A 80"` (current)
- Desktop (`lg:` breakpoint): `"A · Man 80"` — add truncated category name

#### F2: Learn tab — educational experience overhaul

**Current**: 5 buttons → sign grid. No teaching.

**New structure** — each lesson is a mini-course page:

```
┌──────────────────────────────────────────────┐
│  ← Back to Lessons     Step 1 of 5           │
│                                               │
│  🏛️ The Egyptian Alphabet                     │
│  25 single-consonant signs                    │
│                                               │
│  ┌─ Introduction ──────────────────────────┐  │
│  │ Ancient Egyptians wrote only consonants │  │
│  │ — no vowels at all! These 25 signs      │  │
│  │ each represent one consonant sound...   │  │
│  └─────────────────────────────────────────┘  │
│                                               │
│  💡 Tip: Add an 'e' between consonants to    │
│     pronounce: nfr → "nefer" (beautiful)     │
│                                               │
│  ┌─ Signs ────────────────────────────────┐   │
│  │ 𓄿  A   "glottal stop, like uh-oh"     │   │
│  │ 𓇋  i   "ee, like in see"              │   │
│  │ 𓇌  y   "y, like in yes"               │   │
│  │ 𓂝  a   "ah, like in father"           │   │
│  │ ...                                    │   │
│  └────────────────────────────────────────┘   │
│                                               │
│          Next: Common Biliterals →            │
└──────────────────────────────────────────────┘
```

Key changes:
- **Intro paragraphs** rendered above the sign grid (from API `intro_paragraphs`)
- **Tip box** with gold-bordered callout (from API `tip`)
- **Lesson navigation**: "← Back to lessons" + "Next: [title] →"  
- **Progress indicator**: "Step 1 of 5" + progress dots
- **Sign cards in Learn mode are LARGER** (like flashcards):
  - Giant glyph (6xl or 7xl)
  - Transliteration (or "= meaning" or "classifier")
  - One-line pronunciation guide (for uniliterals) OR description (for others)
  - Cards use the `reading` field from the API for the subtitle line

#### F3: Detail modal — type-aware redesign

**Current**: Shows Transliteration + Phonetic Value (always identical), both often "—".

**New modal** — adapts to sign type:

For **phonetic signs** (uni/bi/triliteral):
```
     𓂋                          ← giant glyph
     D21                         ← code
     
  Sound          r               ← transliteration in gold
  Pronunciation  like 'r' in     ← English guide (uniliterals only)
                 'run'
  Type           ● uniliteral    ← colored badge
  Category       D · Parts of    ← full name
                 the Human Body
  Depicts        mouth           ← description
  
  [Fun fact box if available]
  
  [Use in Write →]              ← only for phonetic signs
```

For **determinatives**:
```
     𓂻                          ← giant glyph
     D54                         ← code

  ⓘ This sign is SILENT         ← prominent callout!
  
  Classifier     motion,         ← determinative_class
  for            walking
  Type           ● determinative ← orange badge
  Category       D · Parts of
                 the Human Body
  Depicts        legs walking    ← description
  
  💡 Appears at the end of words
     related to movement
```

For **logograms**:
```
     𓋹                          ← giant glyph
     S34                         ← code
     
  Means          life; to live   ← logographic_value in green
  Sound          anx             ← transliteration
  Type           ● logogram      ← green badge
  Category       S · Crowns...
  Depicts        ankh sign       ← description
  
  [Fun fact box if available]
  
  [Use in Write →]
```

**Key differences**:
- Remove duplicate "Phonetic Value" row
- Add "This sign is silent" callout for determinatives
- Show `reading` field (from API) as the primary subtitle
- Show pronunciation guide for uniliterals
- Fun fact box (gold-bordered) for important signs
- Conditionally show/hide "Use in Write" (hide for determinatives)

#### F4: Empty state improvements

When browsing a category with many determinatives (like A with 76 of 80), add a contextual hint:
> "Most signs in this category are determinatives — silent classifier signs placed at word endings."

---

### Changes — Data (gardiner.py)

#### D1: Remove `phonetic_value` duplication

In `_make_sign()`, stop setting `phonetic_value=phon` redundantly. Instead:
- `transliteration` = the MdC transliteration value (or "" if none)
- `phonetic_value` = remove from GardinerSign dataclass OR keep as deprecated alias

Actually, to avoid breaking write.py and transliteration.py (which use `phonetic_value`), we keep `phonetic_value` in the dataclass as-is but the **API** stops returning it. The API returns the new `sound` and `reading` fields instead. Internal code keeps working.

#### D2: Fun facts dict (~50 entries)

New dict in `dictionary.py` for the most interesting/important signs:
```python
_FUN_FACTS = {
    "G1": "The Egyptian vulture (Neophron percnopterus) was so common in inscriptions that it became the default 'A' sound — appearing in royal names, religious texts, and everyday records.",
    "S34": "The ankh ☥ is the most universally recognized Egyptian symbol. Its origins are debated — theories range from a sandal strap to a mirror to a ceremonial knot.",
    "D21": "The mouth sign is one of the most frequent hieroglyphs. As a logogram, it means 'mouth' (r); as a phonogram, it gives the sound 'r'.",
    "M17": "The single reed represents the sound 'i' and appears in countless words. Two reeds together (M18) represent 'y'.",
    "N5": "The sun disk was central to Egyptian religion — it represents Ra, the sun god, and appears in words meaning 'sun', 'day', and 'time'.",
    ... (about 45 more for key signs)
}
```

---

### Files Modified

| File | Changes |
|------|---------|
| `app/api/dictionary.py` | Smart `_sign_to_dict()`, pronunciation guide dict, lesson intro content, fun facts dict, fix "24"→"25" |
| `app/templates/dictionary.html` | Type-aware cards (Browse), lesson course UI (Learn), type-aware modal, empty state hints |
| `app/core/gardiner.py` | No structural changes needed — API layer handles presentation |
| `app/static/css/input.css` | Possible new component classes for lesson UI (callout boxes, etc.) |

### Files NOT Modified

- `app/core/gardiner_data/*.py` — Raw data stays as-is
- `app/core/gardiner.py` — Internal dataclass unchanged (backward compat)
- `app/api/write.py` — No changes
- `app/core/transliteration.py` — No changes

---

### Implementation Order

1. **dictionary.py** — Add `_PRONUNCIATION_GUIDE`, `_FUN_FACTS`, `_LESSON_CONTENT` dicts. Rewrite `_sign_to_dict()` to produce smart `reading`/`sound` fields. Extend lesson endpoint responses. Fix "24→25".
2. **dictionary.html** — Rewrite Browse cards (type-aware), Learn tab (course UI with intro/tip/progress/nav), detail modal (type-aware), empty state hints.
3. **input.css** — Add callout/tip component if needed.
4. **Build + test** — `npm run build`, bump cache v17→v18, verify all endpoints + visual check.

---

### Self-Prompt (for AI continuation)

```
I'm working on Wadjet v2, Task T3.1: Dictionary UX Overhaul & Learning Journey.

Context:
- T3 (data expansion to 1023 signs) is DONE — 26 category files in gardiner_data/
- ~79% of signs are determinatives with no phonetic value
- The current UI shows "—" dashes everywhere with no explanation
- Transliteration and phonetic_value are always identical

Goal: Transform the dictionary from a data dump into a guided educational experience.

Read these files first:
1. planning/EXPANSION_PLAN.md — find T3.1 section for the full plan
2. app/api/dictionary.py — current API (~230 lines)
3. app/templates/dictionary.html — current template (~415 lines)
4. app/core/gardiner.py — data facade (~200 lines) — DO NOT modify structure

Implementation order:
1. dictionary.py — smart serialization, pronunciation guide, lesson content, fun facts
2. dictionary.html — type-aware cards, course-style Learn tab, type-aware modal
3. input.css — callout components if needed
4. Build CSS, bump cache v17→v18, test

Design rules:
- Black & Gold theme (--color-night bg, --color-gold accents)
- Never use --color-bg (conflicts with TailwindCSS v4)
- Fonts: Playfair Display headings, Inter body, Noto Sans Egyptian Hieroglyphs for glyphs
- Alpine.js for state, HTMX if needed, no React/Vue

When done, update T3.1 status to DONE in planning/EXPANSION_PLAN.md.
```

---

## T3.2: Dictionary — Premium Learning Experience

### Status: DONE ✅

### Problem Statement

T3.1 fixed the data layer (no more "—" everywhere) but the **presentation** is still a data dump, not a learning experience:

1. **Sign detail modal is a flat table** — rows of "Sound / Pronunciation / Type / Category / Depicts" feel like a database record, not a teaching moment. No visual hierarchy, no breathing room, no delight.
2. **Text layout is uncomfortable** — dense info rows with poor spacing. The glyph sits on top, then a wall of key-value pairs. A learner doesn't know where to look first.
3. **Lesson pages are just grids of signs** — no narrative structure. You get intro paragraphs in a box, then a grid of small flashcards. No story, no pacing, no practice.
4. **No example words** — you learn a sign but never see it used in a real Egyptian word. Without examples, signs stay abstract.
5. **No audio** — for an alphabet-based script, being able to hear the sounds is critical for retention.
6. **Emoji usage** — 💡 and ✦ violate the design system. The project uses Lucide SVG icons, not emoji.
7. **Browse cards are too small and uniform** — every sign looks the same regardless of importance. Featured/common signs should stand out.
8. **No inter-page navigation** — from a lesson, you can't quickly jump to see other signs in the same category or related signs.

### Design Philosophy

> "A complete, integrated learning experience — not a dictionary with lessons bolted on."

Principles:
- **Narrative first**: Every page tells a story. Signs are introduced with context.
- **Visual hierarchy**: The glyph is the hero. Supporting info is layered by importance.
- **Show, don't tell**: Example words with sign highlighted > dry descriptions.
- **Practice retention**: End-of-lesson word building, mini-quiz prompts.
- **Audio matters**: Browser SpeechSynthesis for Egyptological pronunciation (free, no files).
- **Design system compliance**: No emoji. Lucide SVGs for icons. Gold/dark theme throughout.

### Inspiration Sources

- **Skills**: `ui-ux-pro-max` (visual hierarchy, animation timing 150-300ms, no-emoji-icons rule), `frontend-design` (intentional aesthetics, visual memorability), `scroll-experience` (scroll-driven reveals, progress indicators)
- **Design system**: Existing `input.css` components (card-glow, badge-gold, btn-shimmer, hvr-glow, hvr-sweep-gold, border-beam, text-gold-animated)
- **Differentiation anchor**: "If screenshotted with logo removed, the Black & Gold + hieroglyphs + Egyptian aesthetic makes this unmistakable"

---

### Changes Overview

#### B1: Lesson Page (Full-Page Route, Not Modal)

**Current**: Lessons render inside the dictionary tab as a grid of flashcards.
**New**: Each lesson gets a dedicated full-page route `/dictionary/lesson/{n}` with proper narrative pacing.

**Page structure** (top to bottom):
1. **Hero section** — Lesson number badge, title (Playfair Display), subtitle, decorative hieroglyph pattern background
2. **Progress bar** — 5-step gold dots with labels, current step highlighted, clickable
3. **Introduction** — 2-3 well-spaced paragraphs with proper typography (line-height 1.75, max-width 65ch). No emoji — use Lucide `info` icon for tip callout instead of 💡
4. **Signs gallery** — Large sign cards in a responsive grid. Each card: big glyph (6xl), Gardiner code badge, transliteration/reading, pronunciation with speaker icon, short description. Clicking opens inline detail (expand-in-place), not a separate modal.
5. **Example words section** — "See it in action" — 3-5 Egyptian words that use signs from this lesson. Each word: hieroglyphic sequence, transliteration, translation, with the lesson's sign highlighted in gold.
6. **Practice prompt** — "Can you read this?" — Show 1-2 simple words using lesson signs. Reveal-on-click answer.
7. **Lesson navigation** — Previous/Next as full-width cards with lesson preview, not small buttons.

**Backend changes**:
- New route: `GET /dictionary/lesson/{n}` → renders `lesson_page.html` (Jinja2 template)
- New data: `_EXAMPLE_WORDS` dict — 3-5 example words per lesson with sign sequences, transliteration, translation, and which signs are highlighted
- New data: `_PRACTICE_WORDS` dict — 1-2 practice words per lesson with hidden answer

#### B2: Sign Detail Redesign (Full-Width Inline Expand or Modal 2.0)

**Current**: Modal with flat key-value rows.
**New**: Rich detail panel with visual hierarchy and sections.

**Layout** (inside modal or inline expand):
1. **Hero zone** — Giant glyph (8xl) centered, with subtle gold glow background behind it. Code displayed below in mono font.
2. **Primary identity** — What this sign IS, front and center:
   - Phonetic signs: Big transliteration with pronunciation underneath + speaker icon (SpeechSynthesis)
   - Logograms: "Means: [value]" in large green text
   - Determinatives: "Silent classifier" callout with category icon
3. **Info cards** (not rows) — Small cards arranged in a 2x2 or 2x3 grid:
   - "Type" card with colored badge
   - "Category" card with Gardiner category + full name
   - "Depicts" card with description
   - "Fun fact" card (if available) with Lucide `sparkles` icon (replacing ✦ emoji)
4. **Example words** — "Used in" section showing 1-3 words that contain this sign
5. **Related signs** — "See also" showing 2-4 related signs from the same category or same sound group
6. **Action** — "Use in Write" button (phonetic signs only), "View in Lesson" link

#### B3: Audio Pronunciation via SpeechSynthesis

**Strategy**: Use the browser's built-in `SpeechSynthesis` API — zero cost, no files to host.

**Implementation**:
- Create a JS function `speakSign(transliteration, type)` that:
  1. Maps Egyptological transliteration to approximate English phonemes (e.g., "nfr" → "nefer", "anx" → "ankh", "Htp" → "hotep")
  2. Uses `speechSynthesis.speak()` with English voice, slow rate (0.7)
  3. For uniliterals, speaks the pronunciation guide value (e.g., "glottal stop" for A, "sh" for S)
- Lucide `volume-2` SVG icon as the trigger (not an emoji)
- Available on: sign detail, lesson cards, example words

**Transliteration-to-speech mapping** (in dictionary.py):
- Already have `_PRONUNCIATION_GUIDE` for 25 uniliterals
- Add `_SPEECH_MAP` for common bi/triliterals and logograms: ~30 entries covering lesson signs
- Return `speech_text` field in the sign API response

#### B4: Example Words Data

**New data structure** in `dictionary.py`:

```python
_EXAMPLE_WORDS: dict[int, list[dict]] = {
    1: [  # Lesson 1 — Alphabet examples
        {
            "hieroglyphs": "𓂋𓏤𓇋𓅱",
            "codes": ["D21", "Z1", "M17", "G43"],
            "transliteration": "r-i-w",
            "translation": "mouth / to speak",
            "highlight_codes": ["D21", "M17", "G43"],  # signs from this lesson
        },
        # ... 4 more words
    ],
    # ... lessons 2-5
}
```

Target: 5 example words per lesson, 2 practice words per lesson = ~35 words total.

Sources for words:
- `data/translation/corpus.jsonl` — existing translation corpus
- `_FUN_FACTS` — many facts mention real words (nfr, anx, Htp, wAs, mwt, pr)
- Gardiner's sign list canonical examples
- Common words from the existing write feature vocabulary

#### B5: Browse Cards Enhancement

**Current**: Uniform small cards for all 1000+ signs.
**New**: Size variation based on sign importance + better hover.

- **Featured signs** (uniliterals + signs with fun_facts): Slightly larger card with glow border on hover
- **Hover effect**: Use existing `card-glow` class + `hvr-float-gold` for lift effect
- **Card inner layout**: Glyph on left (large), code + reading on right (stacked). More horizontal, less stacked.
- **Quick-preview on hover**: Show first line of fun_fact or description in a tooltip/popover (Alpine.js x-tooltip or custom)

#### B6: Replace All Emoji with Lucide SVGs

**Audit of current emoji usage** in dictionary.html:
- `💡` in tip callout → Replace with Lucide `lightbulb` SVG (gold color)
- `✦` in fun fact box → Replace with Lucide `sparkles` SVG (gold color)
- `ⓘ` in determinative callout → Replace with Lucide `info` SVG (orange color)
- `𓊹` in breadcrumb and empty state → This is a hieroglyph Unicode, keep it (it IS the content domain)

**Lucide SVG approach**: Inline SVGs (already used in nav, buttons). Simply paste the SVG path for each icon.

#### B7: CSS Enhancements

**New animations/effects** for lesson pages and sign detail:
- **Sign reveal**: Staggered `fade-up` on lesson sign cards (using CSS `animation-delay` with Alpine index)
- **Glyph entrance**: Scale-up from 0.8 to 1.0 with gold shadow pulse when sign detail opens
- **Section dividers**: Use existing `divider` class (gold gradient line) between lesson sections
- **Lesson hero background**: Subtle `dot-pattern-gold` with radial gradient fade at edges
- **Practice word reveal**: Gold `hvr-sweep-gold` effect on the "reveal answer" button

**No new keyframes needed** — reuse existing `fade-up`, `pulse-gold`, `gradient-sweep`, `shimmer`.

---

### Implementation Order

1. **B4 first** — Build example words data (prerequisite for B1 and B2)
2. **B6 second** — Emoji cleanup (small, quick win, touches all affected templates)
3. **B3 third** — SpeechSynthesis audio (JS utility, independent)
4. **B2 fourth** — Redesign sign detail modal (uses B3 audio + B4 words)
5. **B1 fifth** — Full lesson pages (uses all of the above)
6. **B5 sixth** — Browse cards enhancement
7. **B7 last** — CSS polish and animations

### Files Affected

| File | Changes |
|------|---------|
| `app/api/dictionary.py` | Add `_EXAMPLE_WORDS`, `_PRACTICE_WORDS`, `_SPEECH_MAP`, `speech_text` field, lesson page route |
| `app/api/pages.py` | Add route `GET /dictionary/lesson/{n}` → renders lesson_page.html |
| `app/templates/dictionary.html` | Redesign detail modal (B2), enhance browse cards (B5), fix emoji (B6) |
| `app/templates/lesson_page.html` | NEW — Full-page lesson template (B1) |
| `app/static/css/input.css` | B7 — Lesson hero styles, sign reveal animation, practice word styles |
| `app/static/js/app.js` | B3 — `speakSign()` global function using SpeechSynthesis |

### Quality Checklist

- [ ] No emoji anywhere in dictionary/lesson templates (Lucide SVGs only)
- [ ] Every lesson has 5+ example words and 2+ practice words
- [ ] Audio works for all 25 uniliterals and common bi/triliterals
- [ ] Sign detail shows "Used in" words section
- [ ] Sign detail shows "See also" related signs
- [ ] Lesson pages have proper narrative pacing (hero → intro → signs → examples → practice → nav)
- [ ] Browse cards have size variation (featured vs. normal)
- [ ] All animations use existing keyframes (no new @keyframes unless essential)
- [ ] CSS rebuilt, cache version bumped
- [ ] Responsive: lesson pages and sign detail work on mobile
- [ ] Accessible: speaker buttons have aria-labels, practice reveals work with keyboard
- [ ] Typography: body text at 1.6+ line-height, max-width 65ch for reading sections

---

### Self-Prompt (paste to start T3.2)

```
I'm working on Wadjet v2, Task T3.2: Dictionary — Premium Learning Experience.

Context files to read first:
1. planning/EXPANSION_PLAN.md — find T3.2 section for the full plan
2. app/api/dictionary.py — current dictionary API with type-aware serialization
3. app/templates/dictionary.html — current dictionary template
4. app/static/css/input.css — available CSS components and animations
5. app/templates/base.html — layout template
6. app/static/js/app.js — global JS (where to add speakSign)
7. data/translation/corpus.jsonl — source for example words

CRITICAL design rules:
- Black & Gold theme, NO emoji (use Lucide inline SVGs)
- Fonts: Playfair Display for headings, Inter for body, Noto Sans Egyptian Hieroglyphs for glyphs
- Style: card-glow, badge-gold, hvr-glow, text-gold-animated, border-beam, dot-pattern-gold
- Alpine.js for interactivity, HTMX for server interaction
- Animation timing: 150-300ms for micro-interactions

Implementation order: B4 (data) → B6 (emoji fix) → B3 (audio) → B2 (detail redesign) → B1 (lesson pages) → B5 (browse cards) → B7 (CSS polish)

When done, update T3.2 status to DONE in planning/EXPANSION_PLAN.md.
```

---

## T4: Write Page — Fix & Real Egyptian Translation

### Status: PHASE 1 DONE ✅ — Phase 2 NOT STARTED

### Overview
T4 has two phases:
- **Phase 1**: Fix the 5 bugs that make the Write page completely non-functional
- **Phase 2**: Build a vocabulary-grounded AI translation engine that produces **real Egyptian hieroglyphic writing** — not just letter substitution, but actual words with determinatives, phonetic complements, and proper grammar

### Problem (Phase 1)
The "Write in Hieroglyphs" page (`/write`) is **completely broken** — the page renders blank or shows raw JavaScript source text. Additionally, case-sensitivity bugs cause wrong glyphs, Unicode errors show wrong characters, and Smart Write mode (AI-powered) is unreachable from the UI.

### Bugs Found (5)

#### Bug #1 — CRITICAL: writeApp() function never defined
- **File**: `app/templates/write.html` lines 168-169
- **Symptom**: Page blank (x-cloak hides all), Alpine throws `ReferenceError: writeApp is not defined`, or raw JS code renders as visible page text
- **Root Cause**: After `</section>` (L168), the file jumps directly to `return {` (L169). The following 4 lines are missing between them:
  ```
  {% endblock %}
  {% block scripts %}
  <script>
  function writeApp() {
  ```
  Without these, the Alpine `x-data="writeApp()"` on the `<section>` tag (L11) has no function to call. The `return { ... }` block and closing `}</script>{% endblock %}` at the end (L300-302) have no matching opening.
- **Fix**: Insert the 4 missing lines between L168 and L169.

#### Bug #2 — HIGH: Case-sensitivity destruction in MdC/reverse mapping
- **File**: `app/api/write.py` lines 37-42 and line 175
- **Symptom**: Entering "H" (reed shelter) gives you "h" (wick) = wrong hieroglyph. Same for S/s, T/t, D/d, A/a — 5 pairs of distinct Egyptian consonants become indistinguishable.
- **Root Cause**: `_build_reverse_map()` calls `.lower()` on both `phonetic_value` and `transliteration` before inserting into lookup dict. The uppercase key is overwritten by the lowercase match (or vice versa). MdC branch (L175) also does `remaining = token.lower()`.
- **Fix**: Remove ALL `.lower()` calls from `_build_reverse_map()`. Instead, store both the original-case key AND add lowercase as fallback only if no existing entry. In MdC mode, try exact case first, then lowercase fallback.

#### Bug #3 — MEDIUM: Wrong Unicode codepoints for V31 and W11
- **File**: `app/core/gardiner.py` lines 99-102
- **Symptom**: Letters 'k' (basket) and 'g' (jar stand) show wrong glyphs — V31 shows 𓊨 (Q1, throne/seat) and W11 shows 𓊮 (Q7, brazier)
- **Root Cause**:
  - V31 has `unicode_char="\U000132A8"` — this is U+132A8 which is Q1 (seat). Correct is `\U000133A1` (U+133A1).
  - W11 has `unicode_char="\U000132AE"` — this is U+132AE which is Q7. W11 should be `\U000133BC` (U+133BC, jar stand).
- **Fix**: Remove the wrong `unicode_char=` from V31 and W11 GardinerSign constructors. Add correct entries to `_GARDINER_UNICODE` dict: `"V31": "\U000133A1"` and `"W11": "\U000133BC"`. The backfill loop (L580+) will then apply the correct characters.

#### Bug #4 — MEDIUM: Smart Write button missing from UI
- **File**: `app/templates/write.html` lines 32-37
- **Symptom**: Only 2 mode buttons exist (Alphabetic, MdC Notation). Users cannot access Smart Write mode even though the backend fully supports it (`_ai_translate_to_hieroglyphs()` in write.py L87-132 uses Gemini).
- **Root Cause**: The third button was never added to the template.
- **Fix**: Add a third button after the MdC button:
  ```html
  <button @click="mode = 'smart'" :class="mode === 'smart' ? 'btn-gold' : 'btn-ghost'" class="text-sm">
    <svg>...</svg> Smart Write (AI)
  </button>
  ```
  Also add a brief description text under the input that changes based on mode (Alpine `x-show`):
  - alpha: "Type English letters, get uniliteral hieroglyphs"
  - mdc: "Type Manuel de Codage notation (e.g., 'nfr-xpr')"
  - smart: "Type any English text — AI translates to proper hieroglyphs"

#### Bug #5 — LOW: Minor data inconsistencies in UNILITERALS
- **File**: `app/core/gardiner.py` lines 103-106
- **Symptom**: D4 (eye, 'ir'), D19 (nose, not uniliteral), F35 (heart, not uniliteral) are in the UNILITERALS dict but they are biliterals/triliterals with wrong `SignType.UNILITERAL`.
- **Root Cause**: Data entry error — these signs were placed in the wrong dict.
- **Fix**: Move D4/D19/F35 from UNILITERALS to BILITERALS with correct SignType. Or keep them in UNILITERALS as convenience aliases but fix their sign_type to BILITERAL/TRILITERAL.

### How T3 Improves Write
When T3 is complete (750+ signs with correct Unicode, proper type classification, and comprehensive transliteration data), the Write feature benefits massively:
- **Palette**: The sign picker (`/api/write/palette`) serves ALL signs grouped by category — users can browse/click any of 750+ hieroglyphs
- **MdC mode**: With proper transliterations for all signs, MdC input resolves to many more glyphs
- **Smart mode**: AI can reference a much larger sign inventory in the system prompt
- **Unicode accuracy**: All signs have verified Unicode codepoints — no more wrong glyph display

**Therefore: T4 Phase 1 bug fixes should be done BEFORE T3 (fix the structural/logic bugs), and T3 will then supercharge the Write feature with data. T4 Phase 2 (real translation) should be done AFTER T3 when the full 750+ sign inventory is available.**

### Detailed Implementation Steps — Phase 1 (Bug Fixes)

#### Step 1: Fix Template Structure (Bug #1 — CRITICAL)
**File**: `app/templates/write.html`

Between line 168 (`</section>`) and line 169 (`return {`), insert:
```
{% endblock %}

{% block scripts %}
<script>
function writeApp() {
```

Verify: Line 300-302 should already have `}</script>{% endblock %}` which closes this.
After fix: The page should render — Alpine.js can now find `writeApp()`.

#### Step 2: Fix Case Sensitivity (Bug #2)
**File**: `app/api/write.py`

In `_build_reverse_map()` (lines 34-50):
- Remove `.lower()` from `sign.phonetic_value` and `sign.transliteration` lookups
- Use a `seen` set to track keys already inserted
- For fallback: add lowercase version ONLY if the lowercase key isn't already in the map

In MdC branch (~line 175):
- Remove `remaining = token.lower()`
- Try exact-case lookup first: `if remaining in _REVERSE_MAP`
- Then try lowercase fallback: `elif remaining.lower() in _REVERSE_MAP`

#### Step 3: Fix Unicode Codepoints (Bug #3)
**File**: `app/core/gardiner.py`

Lines 99-102 — Remove `unicode_char="\U000132A8"` from V31 constructor, remove `unicode_char="\U000132AE"` from W11 constructor.

In `_GARDINER_UNICODE` dict (~line 500+), add:
```python
"V31": "\U000133A1",  # basket (k)
"W11": "\U000133BC",  # jar stand (g)
```

The backfill loop will then apply these correct values.

#### Step 4: Add Smart Write Button (Bug #4)
**File**: `app/templates/write.html`

After the two existing mode buttons (~line 37), add:
```html
<button @click="mode = 'smart'"
        :class="mode === 'smart' ? 'btn-gold' : 'btn-ghost'"
        class="text-sm flex items-center gap-1">
  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg>
  Smart Write (AI)
</button>
```

Add mode description below the input area (Alpine `x-text` or `x-show`):
```html
<p class="text-xs text-dust mt-1" x-show="mode === 'alpha'">Type English letters → uniliteral hieroglyphs</p>
<p class="text-xs text-dust mt-1" x-show="mode === 'mdc'">Type MdC notation (e.g., nfr-xpr) → hieroglyphs</p>
<p class="text-xs text-dust mt-1" x-show="mode === 'smart'">Type any text — AI translates to proper hieroglyphs (requires internet)</p>
```

#### Step 5: Fix Data Inconsistencies (Bug #5)
**File**: `app/core/gardiner.py`

Move D4, D19, F35 from `UNILITERALS` dict to `BILITERALS` dict. Update their `sign_type` from `SignType.UNILITERAL` to appropriate type (D4→BILITERAL, D19→BILITERAL, F35→TRILITERAL). Or simply fix `sign_type` in place if keeping them as convenience aliases.

#### After T4 is complete:
```bash
cd "D:\Personal attachements\Projects\Final_Horus\Wadjet-v2"
npm run build
# Bump cache version in base.html: ?v=15 → ?v=16
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Test: http://localhost:8000/write
# Verify:
#   1. Page renders (not blank, no raw JS visible)
#   2. Alphabetic mode: type "ankh" → see correct hieroglyphs
#   3. MdC mode: type "H" (reed shelter) — NOT same as "h" (wick)
#   4. Smart Write button visible and functional (if Gemini key set)
#   5. Letters 'k' and 'g' show correct glyphs (basket, jar stand)
```

---

### Phase 2: Real Egyptian Translation Engine

> **Goal**: When a user types "Life is beautiful" in Smart Write mode, the output should be
> **real Egyptian hieroglyphic writing** — actual words (𓋹 ankh "life", 𓄤 nfr "beautiful")
> with proper determinatives, phonetic complements, and grammar — NOT just letter-by-letter
> substitution like Alphabetic mode.

#### What "Real" Means in Egyptian Hieroglyphic Writing

Egyptian hieroglyphs are NOT an alphabet. A real word is typically composed of:

1. **Phonetic signs** (uni/bi/triliteral) — spell out the sound of the word
2. **Phonetic complements** — redundant signs that reinforce the reading (e.g., nfr + f + r)
3. **Determinatives** — silent classifying signs at the end that indicate what category the word belongs to
   - A1 (seated man) → male person words
   - B1 (seated woman) → female person words
   - D54 (walking legs) → motion/movement words
   - Y1 (papyrus roll) → abstract/writing words
   - N5 (sun disc) → time/sun words
   - A2 (man with hand to mouth) → eating/speaking/emotion words

**Example: "beautiful" = nfr**
- Written as: F35 (heart+windpipe) + I9 (horned viper, 'f') + D21 (mouth, 'r') + Y1 (papyrus, determinative for abstract)
- Gardiner codes: `F35 I9 D21 Y1`
- Unicode: 𓄤𓆑𓂋𓏛
- The F35 is a TRILITERAL (reads n-f-r), I9 and D21 are PHONETIC COMPLEMENTS (redundant), Y1 is the DETERMINATIVE

**Example: "life" = ankh**
- Written as: S34 (ankh symbol) + Z1 (stroke, logogram marker)
- Or: S34 + N35 (water, 'n') + Aa1 (sieve, 'x') (with phonetic complements)
- Gardiner codes: `S34 Z1` (logographic) or `S34 N35 Aa1` (phonetic)
- The S34 is a TRILITERAL/LOGOGRAM (reads a-n-x AND means "life")

#### Current Problem: Why Smart Write Doesn't Do This

The current `_ai_translate_to_hieroglyphs()` in write.py sends a **bare prompt** to Gemini:
```
"You are an expert Egyptologist. Translate the given text into Egyptian hieroglyphs
using the Gardiner Sign List. Return only the hieroglyphic signs needed."
```

**Problems**:
1. **No vocabulary context** — Gemini has no word list to reference, so it hallucinates Gardiner codes
2. **No determinative rules** — Gemini doesn't know which determinative to use for which word
3. **No phonetic complement patterns** — Gemini doesn't know that "nfr" should be F35+I9+D21
4. **No sign inventory** — Gemini doesn't know which of our 750+ signs are actually available (with Unicode)
5. **No grammar guidance** — no rules for word order, plurals, gender, etc.
6. **No validation** — returned Gardiner codes aren't checked against our data

#### Solution: Vocabulary-Grounded AI Translation

The approach combines **three layers**:

**Layer 1: Egyptian Word Lexicon** (new data file)
A curated JSON file with 500+ common Egyptian words, each including the canonical sign sequence.

**Layer 2: RAG-Powered Vocabulary Injection** 
Inject relevant vocabulary entries + corpus examples into the Gemini prompt so it has actual Egyptian words to work with.

**Layer 3: Post-Processing Validation**
Validate every Gardiner code Gemini returns against our sign inventory, add missing determinatives, fix common errors.

#### Step 6: Build Egyptian Word Lexicon
**New file**: `data/translation/egyptian_lexicon.jsonl`

Format — one JSON object per line:
```json
{"translit": "anx", "english": "life; to live", "signs": ["S34", "N35", "Aa1"], "det": ["Y1"], "class": "noun/verb", "notes": "Also used as logogram S34+Z1"}
{"translit": "nfr", "english": "good; beautiful; perfect", "signs": ["F35", "I9", "D21"], "det": ["Y1", "A1"], "class": "adjective", "notes": "F35 is triliteral n-f-r"}
{"translit": "Htp", "english": "peace; offering; to be satisfied", "signs": ["R4", "X1", "Q3"], "det": ["A2"], "class": "noun/verb", "notes": "R4 is triliteral H-t-p, common in offering formula"}
{"translit": "pr", "english": "house; estate", "signs": ["O1"], "det": ["Z1"], "class": "noun", "notes": "O1 is logogram, add Z1 stroke"}
{"translit": "ra", "english": "Ra; sun; day", "signs": ["N5"], "det": ["Z1"], "class": "noun/deity", "notes": "N5 is logogram"}
{"translit": "nTr", "english": "god; divine", "signs": ["R8", "X1", "D21"], "det": ["A40"], "class": "noun", "notes": "R8 is triliteral n-T-r, A40 is seated god determinative"}
{"translit": "nsw", "english": "king; pharaoh", "signs": ["M23", "X1"], "det": ["A40"], "class": "noun", "notes": "M23 (sedge plant) = 'king of Upper Egypt'"}
```

**Data sources for building the lexicon**:
1. **Mine corpus.jsonl** — extract entries where transliteration is 1-3 tokens (single words). ~3000 candidates from 15,604 entries.
2. **Faulkner's Concise Dictionary of Middle Egyptian** — the standard reference (mentioned in `data/reference/`). ~5000 words, we take the 500 most common.
3. **Thesaurus Linguae Aegyptiae (TLA)** — online at `thotsignlist.org` and GitHub (`thesaurus-linguae-aegyptiae/`). The most comprehensive digital Egyptian dictionary.
4. **GitHub reference**: `YomnaWaleed/egyptian-rag-translator` — Hybrid RAG system using TLA dataset with BM25 + dense retrieval. Similar architecture to what we're building.
5. **Wikipedia common words** — extract from the "Simple examples" and "Determinatives" sections of the Egyptian hieroglyphs article.
6. **Our gardiner.py logographic_value field** — signs like S34 (anx="life"), F35 (nfr="beautiful"), N5 (ra="sun") already have word meanings.

**Target: 500+ words** covering:
| Category | Count | Examples |
|----------|-------|---------|
| Common nouns | 150+ | house, water, bread, field, sky, earth, mountain |
| Verbs | 100+ | go, come, give, say, see, make, know, live, die |
| Adjectives | 50+ | good, great, beautiful, strong, old, new |
| Deity names | 30+ | Ra, Amun, Osiris, Isis, Horus, Thoth, Anubis |
| Royal titles | 20+ | king, lord, pharaoh, son of Ra |
| Body parts | 30+ | eye, mouth, hand, heart, face |
| Nature | 40+ | sun, moon, star, water, river, tree, flower |
| Abstract | 40+ | life, death, truth, justice (maat), eternity |
| Common phrases | 40+ | "given life", "lord of the two lands", offering formula |

**Script to build**: Create `scripts/build_lexicon.py` to:
1. Parse corpus.jsonl for single-word entries
2. Cross-reference transliterations with gardiner.py sign data
3. Generate candidate entries with determinative suggestions
4. Output to `data/translation/egyptian_lexicon.jsonl`
5. Manual review/correction pass needed for accuracy

#### Step 7: Create Vocabulary Index for RAG
**New logic in**: `app/core/write_translator.py` (new file)

Build a lightweight lookup system:
```python
# Load lexicon on startup
LEXICON: dict[str, dict] = {}  # translit → lexicon entry
ENGLISH_INDEX: dict[str, list[str]] = {}  # english word → list of transliterations

def _load_lexicon():
    """Load egyptian_lexicon.jsonl into memory."""
    ...

def lookup_by_english(word: str) -> list[dict]:
    """Find Egyptian words matching an English word/concept."""
    ...

def lookup_by_translit(translit: str) -> dict | None:
    """Find lexicon entry by MdC transliteration."""
    ...
```

Also : embed the lexicon descriptions + English meanings into a small FAISS index for semantic lookup. When user types "The king goes to the temple", semantic search finds "king" → nsw, "go" → šm, "temple" → Hwt-nTr.

#### Step 8: Upgrade Smart Write Prompt
**File**: `app/api/write.py` — rewrite `_ai_translate_to_hieroglyphs()`

The new prompt structure (inspired by rag_translator.py pattern):

```python
system = (
    "You are an expert Egyptologist specializing in Middle Egyptian hieroglyphic writing.\n"
    "Your task: translate English text into AUTHENTIC Egyptian hieroglyphic sequences.\n\n"
    "RULES:\n"
    "1. Use REAL Egyptian words from the vocabulary provided below\n"
    "2. Each word MUST include: phonetic signs + phonetic complements + determinative\n"
    "3. Determinatives are SILENT signs at the end of each word that classify its meaning\n"
    "4. Use logographic writing (sign + Z1 stroke) for common nouns when appropriate\n"
    "5. Word order: typically Verb-Subject-Object (VSO) in Middle Egyptian\n"  
    "6. For words NOT in the vocabulary, use phonetic spelling with appropriate determinative\n"
    "7. ONLY use Gardiner codes from the AVAILABLE SIGNS list below\n"
    "8. For proper nouns (modern names), spell phonetically with A1/B1 determinative\n\n"
    "DETERMINATIVE GUIDE:\n"
    "- A1 (seated man): male person words\n"
    "- B1 (seated woman): female person words  \n"
    "- A40 (seated god): deity/divine words\n"
    "- D54 (walking legs): motion/movement verbs\n"
    "- Y1 (papyrus roll): abstract concepts, writing\n"
    "- A2 (man hand-to-mouth): eating, speaking, emotion\n"
    "- N5 (sun): time, sun, light\n"
    "- O1 (house): buildings, places\n"
    "- N25 (desert hills): foreign lands, desert\n"
    "- Z1 (stroke): marks logographic usage\n\n"
)

# Inject vocabulary context
vocab_context = "VOCABULARY (use these Egyptian words):\n"
for entry in relevant_vocab_entries:
    vocab_context += (
        f"- '{entry['english']}' = {entry['translit']} "
        f"→ signs: {' '.join(entry['signs'])} "
        f"+ det: {' '.join(entry['det'])}\n"
    )

# Inject available signs
signs_context = "AVAILABLE SIGNS (only use these Gardiner codes):\n"
for code, sign in TOP_SIGNS:  # top ~200 most useful signs
    signs_context += f"- {code}: {sign.transliteration} ({sign.description})\n"

prompt = (
    f'Translate to Egyptian hieroglyphs: "{text}"\n\n'
    f'{vocab_context}\n'
    f'Return JSON with word-by-word breakdown:\n'
    f'{{\n'
    f'  "words": [\n'
    f'    {{\n'
    f'      "english": "life",\n'
    f'      "transliteration": "anx",\n'
    f'      "signs": ["S34", "N35", "Aa1"],\n'
    f'      "determinative": ["Y1"],\n'
    f'      "type": "logogram+phonetic"\n'
    f'    }}\n'
    f'  ],\n'
    f'  "reading_order": "right-to-left",\n'
    f'  "grammar_notes": "brief note on word order and grammar choices",\n'
    f'  "confidence": "high/medium/low"\n'
    f'}}'
)
```

**Key improvements over current prompt**:
1. **Vocabulary injection** — AI has actual Egyptian words to use (not hallucinating)
2. **Available signs list** — AI can only use Gardiner codes we actually have
3. **Determinative guide** — explicit rules for which determinative to add
4. **Grammar rules** — VSO word order, etc.
5. **Structured output** — word-by-word breakdown instead of flat list
6. **Confidence scoring** — AI self-reports how confident the translation is

#### Step 9: Post-Processing & Validation
**File**: `app/api/write.py` — new function `_validate_and_enrich()`

After Gemini returns the JSON:
1. **Validate codes**: Check every Gardiner code exists in `GARDINER_TRANSLITERATION`
2. **Fix missing determinatives**: If a word has no determinative, add one based on the determinative categories in gardiner.py
3. **Resolve Unicode**: Map each Gardiner code to its Unicode character
4. **Handle unknowns**: For codes Gemini returned that don't exist, try fuzzy matching (e.g., "A01" → "A1")
5. **Cross-check with lexicon**: If a word in the lexicon has a known sign sequence, prefer that over Gemini's output

```python
async def _validate_and_enrich(ai_result: dict, lexicon: dict) -> dict:
    """Post-process AI translation: validate codes, add determinatives, resolve Unicode."""
    validated_words = []
    for word in ai_result.get("words", []):
        # Check if this word is in our lexicon — prefer canonical spelling
        lex_entry = lexicon.get(word.get("transliteration", ""))
        if lex_entry:
            word["signs"] = lex_entry["signs"]
            word["determinative"] = lex_entry["det"]
            word["source"] = "lexicon"
        else:
            word["source"] = "ai"
        
        # Validate all Gardiner codes
        all_codes = word["signs"] + word.get("determinative", [])
        for code in all_codes:
            sign = GARDINER_TRANSLITERATION.get(code)
            if not sign:
                # Try fuzzy match...
                ...
        
        validated_words.append(word)
    return {"words": validated_words, ...}
```

#### Step 10: Word-by-Word Display UI
**File**: `app/templates/write.html`

Upgrade the result display for Smart mode to show word-by-word breakdown:

```html
<!-- For smart mode: show word breakdown -->
<template x-if="mode === 'smart' && result.words">
  <div class="space-y-3 mt-4">
    <template x-for="word in result.words" :key="word.english">
      <div class="card p-3 flex items-center gap-3">
        <!-- Hieroglyphs (large) -->
        <span class="text-3xl font-hieroglyph" x-text="word.unicode_display"></span>
        <!-- Breakdown -->
        <div class="flex-1">
          <p class="text-gold font-semibold" x-text="word.english"></p>
          <p class="text-ivory text-sm" x-text="word.transliteration"></p>
          <p class="text-dust text-xs">
            Signs: <span x-text="word.signs.join(' + ')"></span>
            <span x-show="word.determinative.length"> + det: <span x-text="word.determinative.join(' ')"></span></span>
          </p>
        </div>
        <!-- Source badge -->
        <span class="badge-gold text-xs" x-text="word.source === 'lexicon' ? '📚 Verified' : '🤖 AI'"></span>
      </div>
    </template>
    <!-- Grammar notes -->
    <p class="text-dust text-xs italic" x-text="result.grammar_notes"></p>
    <!-- Confidence -->
    <div class="flex items-center gap-2 text-xs">
      <span class="text-sand">Confidence:</span>
      <span :class="result.confidence === 'high' ? 'text-green-400' : result.confidence === 'medium' ? 'text-gold' : 'text-red-400'" 
            x-text="result.confidence"></span>
    </div>
  </div>
</template>
```

#### After T4 Phase 2 is complete:
```bash
cd "D:\Personal attachements\Projects\Final_Horus\Wadjet-v2"
npm run build
# Cache version should already be bumped from Phase 1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Test: http://localhost:8000/write
# Verify:
#   1. Smart Write mode: type "Life is beautiful" → get real Egyptian words
#      Expected: 𓋹 ankh (life) + 𓄤𓆑𓂋 nfr (beautiful) with determinatives
#   2. Word-by-word breakdown shows transliteration, signs, determinatives
#   3. Lexicon words show "📚 Verified" badge
#   4. AI-only words show "🤖 AI" badge
#   5. Grammar notes explain word order
#   6. Confidence indicator shows high/medium/low
#   7. Try "the king goes to the temple" — should use nsw, šm, Hwt-nTr
#   8. Try a name "Nour" — should spell phonetically with A1 determinative
```

#### Online Resources & References
| Resource | URL | What to Extract |
|----------|-----|-----------------|
| Thesaurus Linguae Aegyptiae (TLA) | `thotsignlist.org` | Interactive sign database — the authoritative source |
| YomnaWaleed/egyptian-rag-translator | `github.com/YomnaWaleed/egyptian-rag-translator` | Hybrid RAG (BM25+dense) for Egyptian translation, uses TLA dataset |
| Thesaurus Linguae Aegyptiae GitHub | `github.com/thesaurus-linguae-aegyptiae/` | MdC→Unicode keyboard, transliteration standards |
| Wikipedia: Egyptian hieroglyphs | `en.wikipedia.org/wiki/Egyptian_hieroglyphs` | Grammar rules, determinative examples, phonetic complement patterns |
| Faulkner's Concise Dictionary | In `data/reference/` as PDF | Standard Middle Egyptian dictionary (~5000 words) |
| Existing corpus (15,604 pairs) | `data/translation/corpus.jsonl` | Mine for single-word entries, validate against lexicon |

#### Repos to Consult During Phase 2
| Repo | Path | What to Use |
|------|------|-------------|
| `antigravity-awesome-skills/skills/prompt-engineering-patterns/` | `Repos/` | Few-shot selection, Chain-of-Thought prompting |
| `antigravity-awesome-skills/skills/rag-engineer/` | `Repos/` | Hybrid search (BM25+vector), reranking patterns |
| `antigravity-awesome-skills/skills/llm-app-patterns/` | `Repos/` | Embedding model comparison, vocabulary grounding |
| `sentence-transformers/examples/training/` | `Repos/` | Fine-tuning embeddings on Egyptian data (future upgrade) |
| `ragflow/rag/prompts/` | `Repos/08-RAG-VectorDB/` | Cross-language prompt templates |

#### NEW API Providers for T4-P2 (from research)

These free APIs dramatically improve translation quality and reliability:

| Provider | Role in T4-P2 | Free Tier |
|----------|--------------|-----------|
| **Voyage AI** | Primary embedder for lexicon FAISS index (replaces all-MiniLM-L6-v2). Use `voyage-4-large` for semantic English→Egyptian word matching. Use `rerank-2.5` to rerank few-shot examples in translation prompt. | 200M tokens lifetime |
| **TLA API** | Primary data source for building `egyptian_lexicon.jsonl`. 90,000 ancient Egyptian lemmas with transliteration, translation, attestations. `api.thesaurus-linguae-aegyptiae.de` — free, no key. | Free forever, no key |
| **Cloudflare Workers AI** | Backup embedder (`bge-m3` multilingual). Backup text generation for translation when Gemini+Groq both fail. | 10K neurons/day forever |
| **Groq** | Translation fallback when Gemini rate-limited. Use `llama-3.3-70b-versatile` for vocabulary-grounded translation. Also `playai-tts-arabic` for Arabic readback of translations. | 1000 req/day free |
| **Google Cloud TTS** | Read back translations in Arabic Neural voice ("ankh = حياة"). Premium quality multilingual TTS. | 4M chars/month free |
| **Grok** | Tiebreaker when AI translations disagree. Cross-validate Gemini's sign choices. | 8 keys |

**Embedding strategy**: Use Voyage AI `voyage-4-large` as primary (200M tokens is enormous for a 500-word lexicon). Build FAISS index over lexicon English meanings. At query time: embed user input → find top-K matching Egyptian words → inject into Gemini prompt. Fallback: Cloudflare `bge-m3` if Voyage unavailable.

**Translation fallback chain**: Gemini 2.5 Flash (vocabulary-grounded prompt) → Groq Llama 3.3 70B → Grok → Cloudflare Llama → alpha mode (last resort WITH user warning).

#### Write Page Bugs to Fix BEFORE Building Translation Engine

These bugs exist in current code and must be fixed as part of T4-P2:

| Bug | Severity | Issue |
|-----|----------|-------|
| Silent Smart→Alpha fallback | HIGH | When Gemini fails, Smart mode silently degrades to letter-by-letter. User sees no warning. Must show "⚠️ AI unavailable, using phonetic approximation" toast. |
| Palette insertion in Alpha mode | MEDIUM | `insertFromPalette()` appends transliteration string (e.g. "nfr") to alpha input, which gets split letter-by-letter (n→sign, f→sign, r→sign = 3 wrong signs). Fix: in alpha mode, insert the Unicode character directly. |
| No error feedback on API failure | MEDIUM | `write.html`: 4xx/5xx responses log to console only. Add visible error toast/notification. |
| Gemini returns invalid Gardiner codes | MEDIUM | No validation. "A01" instead of "A1", "G01" instead of "G1". Add code normalization: strip leading zeros, validate against `GARDINER_TRANSLITERATION`. |
| corpus.jsonl completely unused | LOW | 15,604 Egyptian↔English translation pairs sit unused by write. With direction reversal, this could power a basic word lookup even without AI. |

#### Mandatory Test Cases

Test these known Egyptian words after implementation. If ANY fail, the translation engine is not working:

| English Input | Expected MdC | Expected Signs | Determinative |
|--------------|-------------|----------------|---------------|
| "life" | anx | S34 N35 Aa1 | Y1 |
| "beautiful" / "good" | nfr | F35 I9 D21 | Y1 |
| "peace" / "offering" | Htp | R4 X1 Q3 | A2 |
| "house" | pr | O1 | Z1 (logogram) |
| "sun" / "Ra" | ra | N5 | Z1 (logogram) |
| "god" | nTr | R8 X1 D21 | A40 |
| "king" | nsw | M23 X1 | A40 |
| "water" | mw | N35 W24 | N35A |
| "The king goes to the temple" | nsw + šm + r + Hwt-nTr | Multiple | VSO order |
| "Nour" (proper name) | n-w-r | N35 G43 D21 | A1 (male) |

### T4 Self-Prompt (copy this when starting T4)

#### Phase 1 Self-Prompt (do this BEFORE T3):
```
I'm working on Wadjet v2, Task T4 Phase 1: Fix the Write in Hieroglyphs page.
Read planning/EXPANSION_PLAN.md for the full plan.

The Write page is COMPLETELY BROKEN due to 5 bugs I've documented.
Fix them in this order:

1. CRITICAL — write.html L168-169: Insert 4 missing lines ({% endblock %},
   {% block scripts %}, <script>, function writeApp() {) between </section>
   and return {. This makes the page render at all.

2. HIGH — write.py _build_reverse_map(): Remove .lower() calls that destroy
   case sensitivity (H/h, S/s, T/t, D/d, A/a are DIFFERENT signs in Egyptian).
   Also fix MdC branch L175 remaining = token.lower().

3. MEDIUM — gardiner.py V31/W11: Remove wrong unicode_char from constructors,
   add correct entries to _GARDINER_UNICODE: V31=\U000133A1, W11=\U000133BC.

4. MEDIUM — write.html: Add Smart Write (AI) button after existing 2 buttons.
   Backend already supports mode='smart' with Gemini integration.

5. LOW — gardiner.py: Move D4/D19/F35 from UNILITERALS to BILITERALS or fix
   their sign_type.

After changes: npm run build, bump cache, test /write route.
When done, update T4 Phase 1 status to DONE in planning/EXPANSION_PLAN.md.
```

#### Phase 2 Self-Prompt (do this AFTER T3 is complete):
```
I'm working on Wadjet v2, Task T4 Phase 2: Real Egyptian Translation Engine.
Read planning/EXPANSION_PLAN.md for the full Phase 2 plan.

T3 should already be done (750+ Gardiner signs available).
Phase 1 should already be done (Write page renders and works).

Now build REAL Egyptian translation for Smart Write mode.

STEPS:
1. Build Egyptian Word Lexicon — create data/translation/egyptian_lexicon.jsonl
   with 500+ common Egyptian words. Each entry: translit, english, signs
   (list of Gardiner codes), det (determinatives), class, notes.
   Use scripts/build_lexicon.py to mine corpus.jsonl for single-word entries,
   cross-reference with gardiner.py, and seed from known words.
   Sources: corpus.jsonl, gardiner.py logographic_value, TLA, Faulkner.
   
2. Create vocabulary lookup — new file app/core/write_translator.py.
   Load lexicon on startup. Provide lookup_by_english() and lookup_by_translit().
   Optionally embed english meanings into small FAISS index for semantic match.

3. Upgrade Smart Write prompt — rewrite _ai_translate_to_hieroglyphs() in
   app/api/write.py. Inject relevant vocabulary entries + available signs list
   into Gemini prompt. Require word-by-word JSON output with signs, determinatives,
   transliteration, and confidence. Use determinative guide in system prompt.
   See the full prompt template in the plan.

4. Add post-processing validation — new _validate_and_enrich() function.
   Validate Gardiner codes against inventory, fix missing determinatives,
   cross-check with lexicon (prefer lexicon over AI for known words).

5. Upgrade Write UI — update write.html Smart mode display to show
   word-by-word breakdown: hieroglyphs, transliteration, meaning, signs,
   determinative, source badge (📚 Verified vs 🤖 AI), grammar notes,
   confidence indicator.

Test with: "Life is beautiful" → expect anx (𓋹) + nfr (𓄤𓆑𓂋)
Test with: "The king goes to the temple" → expect nsw + šm + Hwt-nTr
Test with: "Nour" → expect phonetic spelling with A1 determinative

When done, update T4 Phase 2 status to DONE in planning/EXPANSION_PLAN.md.
```

---

## Execution Order

1. **T1 first** — smallest task, immediate visual improvement — **DONE ✅**
2. **T4 Phase 1 second** — fix Write page bugs (structural, case sensitivity, Unicode, Smart button) — **DONE ✅**
3. **T3 third** — dictionary expansion (177→1023 signs, supercharges everything) — **DONE ✅**
4. **T3.1 fourth** — dictionary UX overhaul & learning journey (fix the 79% "—" problem, add teaching) — **DONE ✅**
5. **T3.2 fifth** — premium learning experience (lesson pages, example words, audio, detail redesign, emoji cleanup)
6. **T4 Phase 2 sixth** — real Egyptian translation engine (needs T3's signs for vocabulary coverage)
7. **T2 last** — explore expansion (largest, affects most files)

> **Why this order?**
> - T4 Phase 1 fixes the broken template so Write page renders at all
> - T3 then expands Gardiner data from 177→750+ signs — this gives Phase 2 the full sign inventory it needs
> - T4 Phase 2 builds the real translation engine using the 750+ signs as its available sign list + lexicon validation
> - T2 is last because it's the largest and most independent

Each task should end with:
- Server restart test (uvicorn)
- Visual check in browser
- CSS rebuild (`npm run build`)
- Cache version bump in `base.html` (`?v=N` → `?v=N+1`)
- Status update in this file
- Git commit

---

## Git Commit Strategy

### Branch
Work on `main` directly (solo project). If you prefer branches:
```bash
git checkout -b feature/expansion-t1
# ... work ...
git checkout main && git merge feature/expansion-t1
```

### Commit Messages (after each task)
| Task | Commit Message |
|------|---------------|
| T1 | `feat(chat): fix Thoth formatting — color hierarchy, table render, spacing` |
| T4-P1 | `feat(write): fix broken Write page — template structure, case sensitivity, Unicode, Smart mode` |
| T3 | `feat(dictionary): complete Gardiner sign list — 750+ hieroglyphs, educational flow` |
| T4-P2 | `feat(write): real Egyptian translation engine — word lexicon, vocabulary-grounded AI, word-by-word display` |
| T2 | `feat(explore): full Egypt heritage expansion — 250+ sites, categories, galleries` |
| Deploy | `chore: prepare for HuggingFace Spaces deployment` |

### When to Commit
- After EACH task is complete and tested
- NOT during a task (keep working set clean)
- After `npm run build` and cache bump

```bash
cd "D:\Personal attachements\Projects\Final_Horus\Wadjet-v2"
git add -A
git status  # review what changed
git commit -m "feat(chat): fix Thoth formatting — color hierarchy, table render, spacing"
# git push origin main  # only when ready
```

---

## HuggingFace Spaces Deployment (After All 4 Tasks)

### Overview
After T1, T4, T3, T2 are all complete and committed, deploy Wadjet v2 to HuggingFace Spaces as a Docker-based app.

### Pre-Deployment Checklist
- [ ] All 4 tasks committed and tested locally
- [ ] `npm run build` produces final `app/static/dist/styles.css`
- [ ] CSS cache version is final in `base.html`
- [ ] No hardcoded localhost URLs in templates
- [ ] Gemini API key(s) are read from environment variables (not hardcoded)
- [ ] ONNX models are in `models/` directory (or fetched at startup)
- [ ] `requirements.txt` is up to date
- [ ] Dockerfile builds and runs locally: `docker build -t wadjet . && docker run -p 8000:8000 wadjet`

### HuggingFace Space Setup

#### 1. Create the Space
- Go to https://huggingface.co/spaces
- Create new Space → Docker SDK
- Name: `wadjet` (or `wadjet-v2`)
- Visibility: Public

#### 2. Configure Dockerfile for HF Spaces
HuggingFace Spaces expects the app on port **7860** by default. Update Dockerfile or use `PORT` env var:
```dockerfile
# In Dockerfile, change the CMD or add:
ENV PORT=7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

Or use the existing Dockerfile if it already reads `$PORT`. Check current Dockerfile:
```bash
# Review current Dockerfile
cat Dockerfile
# Ensure it has: --port ${PORT:-8000} or similar
```

#### 3. Environment Variables (HF Space Settings)
Set these in the Space's Settings → Variables:
| Variable | Value | Secret? |
|----------|-------|---------|
| `GEMINI_API_KEY` | Your Gemini key | Yes (secret) |
| `GEMINI_API_KEYS` | Comma-separated keys for rotation | Yes (secret) |
| `PORT` | `7860` | No |

#### 4. Model Files
Two options for ML models:
- **Option A (Git LFS)**: Push ONNX models via Git LFS to the HF Space repo. Simple but increases repo size.
  ```bash
  git lfs install
  git lfs track "*.onnx"
  git add .gitattributes models/
  git commit -m "chore: add ONNX models via LFS"
  ```
- **Option B (HF Hub download)**: Download models at startup from a HuggingFace model repo. Keeps Space repo small but adds cold-start time.

Recommended: **Option A** for simplicity — total model size is ~300MB which HF Spaces handles fine.

#### 5. Push to HuggingFace
```bash
# Add HF remote
git remote add hf https://huggingface.co/spaces/YOUR_USERNAME/wadjet

# Push everything
git push hf main

# Monitor build at https://huggingface.co/spaces/YOUR_USERNAME/wadjet
```

#### 6. Post-Deploy Verification
- [ ] Space builds successfully (check Logs tab)
- [ ] Landing page loads at `https://YOUR_USERNAME-wadjet.hf.space/`
- [ ] Hieroglyphs path: Scan, Dictionary (750+ signs), Write (all 3 modes)
- [ ] Landmarks path: Explore (250+ sites), Identify
- [ ] Thoth Chat: responds, markdown renders correctly (T1 fix)
- [ ] Quiz: loads and functions
- [ ] No console errors in browser DevTools
- [ ] Mobile responsive layout works

### HF Deployment Self-Prompt
```
I'm deploying Wadjet v2 to HuggingFace Spaces after completing all 4 expansion tasks.
Read planning/EXPANSION_PLAN.md for the deployment checklist.

Steps:
1. Run pre-deployment checklist — verify all tasks done, Docker builds locally
2. Review Dockerfile — ensure PORT env var support (default 7860)
3. Create HF Space (Docker SDK, public)
4. Set environment variables (GEMINI_API_KEY, PORT=7860)
5. Push models via Git LFS (track *.onnx, commit)
6. git push hf main
7. Monitor build logs on HF Spaces
8. Run post-deploy verification checklist
```

---

## Progress Log

| Date | Task | What Was Done | Notes |
|------|------|---------------|-------|
| 2026-03-25 | Planning | Research complete, plan created | All 3 tasks scoped |
| 2026-03-26 | Planning | Added detailed implementation steps, self-prompts, Wikipedia sign data, commit strategy | Plan is now execution-ready |
| 2026-03-26 | Planning | Investigated Write page — found 5 bugs, added T4, HF deployment, updated execution order | 4 tasks + deployment now fully planned |
| 2026-03-27 | Planning | Researched real Egyptian translation — split T4 into Phase 1 (bug fixes) + Phase 2 (real translation engine). Added lexicon spec, vocabulary-grounded prompt design, word-by-word UI, references (TLA, YomnaWaleed/egyptian-rag-translator). Updated execution order: T1→T4P1→T3→T4P2→T2 | Phase 2 needs T3's 750+ signs |
| 2026-03-25 | T1 | DONE — Fixed chat CSS (color hierarchy: H1 gold, H2 gold-light, H3 ivory, bold gold-light, italic ivory@0.85), table styles, list spacing, blockquote border. Rewrote renderMarkdown() with inline formatting inside lists + table parser. Added formatting instructions to Thoth system prompt. Built CSS, bumped cache v15→v16. | All 3 files updated |
| 2026-03-27 | T4-P1 | DONE — Fixed all 5 Write page bugs: (1) Template structure — added missing endblock/script wrapper, page no longer shows raw JS; (2) Case sensitivity — two-pass _build_reverse_map() with exact-case first, lowercase fallback second, all 5 case pairs (t/T, h/H, s/S, d/D, a/A) map to distinct signs; (3) Unicode — V31→U+133A1, W11→U+133BC, added W11 to _GARDINER_UNICODE; (4) Smart Write button added with SVG icon, mode descriptions, smart examples; (5) D4/D19 comment clarified. | write.html, write.py, gardiner.py |
| 2026-03-25 | T3.2 gaps | DONE — Added "Used in" example words + "See also" related signs to detail modal. Backend: `_build_usage_index()` indexes all example words by sign code, `_find_related_signs()` picks 4 signs from same category/type. Enriched `GET /api/dictionary/{code}` with `example_usages` + `related_signs` (paginated list stays lightweight). Frontend: `openDetail()` now async-fetches enriched detail, `fetchAndOpenDetail()` enables navigation between related signs. | dictionary.py, dictionary.html |

---

## Blocked / Open Questions

1. Should pharaohs (Akhenaten, Ramesses II etc.) become separate "Historical Figures" pages or be absorbed into museum/temple content? **Decision: Absorb into parent sites (e.g., Ramesses II info inside Abu Simbel, Karnak, etc.)**
2. For the dictionary, should we generate educational "lesson" pages server-side or client-side? **Decision: Client-side Alpine.js, data from API**
3. Image sourcing for explore: Wikipedia thumbnails are CORS-safe but low-res. Use Wikimedia Commons API for higher-res? **Decision: Yes, upgrade image metadata**

---

## File Quick Reference

| File | Purpose | Lines |
|------|---------|-------|
| `app/static/css/input.css` | Chat CSS styles | ~133-220 |
| `app/templates/chat.html` | Chat UI + renderMarkdown | ~452 |
| `app/core/thoth_chat.py` | Thoth system prompt + streaming | ~200 |
| `app/core/gardiner.py` | Gardiner sign data (177→750+) | ~640 |
| `app/api/dictionary.py` | Dictionary API endpoints | ~145 |
| `app/templates/dictionary.html` | Dictionary UI | ~245 |
| `app/templates/write.html` | Write in Hieroglyphs UI (BROKEN) | ~302 |
| `app/api/write.py` | Write API — 3 modes + palette | ~270 |
| `app/core/write_translator.py` | NEW — Vocabulary lookup for real translation (T4-P2) | — |
| `data/translation/egyptian_lexicon.jsonl` | NEW — 500+ Egyptian words with sign sequences (T4-P2) | — |
| `data/translation/corpus.jsonl` | 15,604 phrase-level MdC↔English pairs | ~15604 |
| `scripts/build_lexicon.py` | NEW — Mine corpus + build lexicon (T4-P2) | — |
| `data/expanded_sites.json` | Site index (157→250+) | ~1100 |
| `data/text/*.json` | Wikipedia extracts (157 files) | varies |
| `data/metadata/*.json` | Image metadata (55 files) | varies |
| `app/core/landmarks.py` | 20 curated ATTRACTIONS | ~400 |
| `app/api/explore.py` | Explore API (3-tier) | ~400 |
| `app/templates/explore.html` | Explore UI | ~600 |
