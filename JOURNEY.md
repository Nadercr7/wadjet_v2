# The Wadjet Journey

---

## Prologue: Where It Started

It began as a graduation project — a simple web app that could identify hieroglyphs from uploaded photos. One classifier, a handful of pages, and a basic upload flow. It barely worked, but it proved the concept: you could point a camera at ancient inscriptions and get something meaningful back. That was enough to keep going.

---

## Chapter 1: The First Version

The first real rewrite expanded the idea into a dual-purpose platform — hieroglyphs and Egyptian landmarks in one place. A scanning pipeline, a landmark explorer, a chatbot named Thoth, a hieroglyph dictionary, and a write feature that could show English words in hieroglyphic sequences.

It shipped. It worked. But the scanning accuracy wasn't reliable enough for real stone inscriptions, and the interface needed a significant rethink. The core idea was right, but the execution needed a clean start.

---

## Chapter 2: The Rebuild

The full rebuild started with a clear vision: **Black & Gold**. A dark Egyptian design system — no light mode, no white backgrounds, no compromises. Gold accents on obsidian surfaces, serif headings paired with clean sans-serif body text, and Noto Sans Egyptian Hieroglyphs for authentic glyph rendering.

The architecture followed a **dual-path** layout — landing on `/`, users choose between the Hieroglyphs path (scan, dictionary, write) and the Landmarks path (explore, identify). Each path has its own hub, and Thoth — the chatbot — serves both.

Feature by feature, the platform took shape:

- **Scan**: Upload or photograph hieroglyphic inscriptions. The system detects individual glyphs, classifies each one, provides transliterations, and translates to English and Arabic. All ML inference runs on-device — nothing leaves the browser.

- **Dictionary**: 1,023 Gardiner signs across all 26 categories. Search by name, phonetic value, or meaning. Progressive lessons for learning the Egyptian alphabet.

- **Write**: Type in English and get hieroglyphic output. Multiple composition modes for different use cases.

- **Explore**: 260+ Egyptian heritage sites — pharaonic temples, Islamic monuments, Coptic churches, Greco-Roman ruins, and even modern experiences like Nile cruises and hot air balloon rides over Luxor.

- **Thoth**: A chatbot with the personality of the Egyptian god of knowledge. Ask anything about Ancient Egypt and get scholarly-grade answers. Voice input and output supported.

- **Quiz**: Test your knowledge of Ancient Egyptian history, monuments, and hieroglyphs.

---

## Chapter 3: The Models

Three custom ML models were trained through multiple iterations to get the accuracy right.

The **hieroglyph classifier** recognizes 171 distinct Gardiner sign classes with **98.2% accuracy**. The **landmark classifier** identifies 52 Egyptian sites with **93.8% accuracy**. The **hieroglyph detector** locates individual glyphs within photographed inscriptions, trained on over 10,000 annotated images combining real photographs and augmented data.

All models are optimized and quantized for minimal size and fast on-device inference. The total model payload is under 50 MB.

When the on-device pipeline encounters difficult inscriptions, an AI vision system steps in for a second opinion. The two approaches cross-validate each other — local models for privacy and speed, AI vision for complex cases.

---

## Chapter 4: The Expansion

After the core was solid, the scope grew:

- The dictionary went from 177 signs to **1,023** — covering every Gardiner category with pronunciation guides and fun facts
- The landmark explorer grew from 56 to **260+** sites, organized into parent-child relationships for complex sites like Karnak Temple
- Smart write mode was added — real Egyptian word translation, not just letter-by-letter substitution
- Voice features: listen to translations being read aloud, speak to the chatbot
- Offline support via Service Worker — scan and dictionary work without internet
- History tracking for scans, translations, and conversations
- A recommendation engine for discovering related landmarks

---

## Chapter 5: By The Numbers (v2)

| What | How Much |
|------|----------|
| Gardiner signs in dictionary | 1,023 |
| Egyptian heritage sites | 260+ |
| Hieroglyph recognition accuracy | 98.2% |
| Landmark recognition accuracy | 93.8% |
| Hieroglyph classes supported | 171 |
| Landmark sites recognized | 52 |
| Total model size (all three) | ~42 MB |
| Image URLs for landmarks | 1,220+ |
| Interactive mythology stories | 12 |
| Translatable hieroglyphs | 88 |

---

## Chapter 6: The v3 Upgrade

The v3 beta took everything from v2 and rebuilt it from the ground up:

- **Security**: Full auth system — register, login, JWT tokens, Google OAuth, email verification via Resend
- **Scan pipeline upgrade**: Improved hieroglyph detection → classification → translation chain
- **Stories**: 13 interactive Egyptian mythology stories with AI-generated illustrations (Cloudflare FLUX.1), TTS narration (Gemini 2.5 Flash), and immersive reading experience
- **Brand identity**: Custom Wadjet serpent logo, full favicon set, branded loading screens
- **Loading experience**: Animated loading overlay with logo scale-in, gold shimmer ring, and branded section loaders across all pages
- **Design polish**: Black & Gold design system consistently applied across every template, `prefers-reduced-motion` support, noscript fallbacks
- **Cleanup**: Removed orphaned v2 model files, zero TODO/FIXME in codebase, all images have alt text, all icon buttons have aria-labels

The v3 codebase was promoted to HuggingFace Spaces as v3.0.0, replacing the original v2 deployment.

---

## Chapter 7: The Archive

With v3 production-ready, the project history was organized into a clean external archive at `Wadjet-v2/`:

- **Original Horus AI** — the graduation project that started it all (Flask app, 254 MB Keras model, demo video, academic papers)
- **v1 reference** — key files from the first FastAPI rewrite
- **v2 codebase** — the complete v2 production code with full git history
- **Training artifacts** — Kaggle notebooks, training results, data catalogs
- **Planning docs** — every spec, plan, constitution, and session log from v2 through v3

The v3-beta repo was cleaned to contain only production code — no archive, no planning docs, no historical artifacts.

---

## Chapter 8: The Polish

With v3 live, the focus shifted to real-world usability — the kind of issues you only find when people actually use the thing.

**UX restructure**: The navigation was simplified. The Write feature merged into the Dictionary as a tab — one less top-level page, cleaner flow. Scan and Dictionary grouped under a "Hieroglyphs" dropdown. Landmarks got its own clear nav entry. Thoth AI kept its spot. The footer attribution updated to the actual author.

**Bilingual lessons**: The dictionary's Learn tab got full Arabic/English lesson support with audio pronunciation on example words and practice exercises. TTS was fixed to pronounce actual Egyptian words instead of spelling them letter by letter.

**Write tab pronunciation**: Instead of translating back to the language the user already typed in (useless), the Write tab now shows the ancient Egyptian transliteration and lets you hear how the hieroglyphs would have been pronounced — using a deep, resonant voice meant to evoke an ancient Egyptian scribe reading aloud in a temple.

**Auth token refresh**: Every page that called `/api/user/*` endpoints (explore favorites, story progress, settings, dashboard) was using raw `fetch()` with a manually-attached token. When the access token expired, these calls silently 401'd with no retry. All replaced with `_authFetch()` — the auth store's wrapper that auto-refreshes expired tokens and retries.

**Dashboard counters**: The scan page wasn't sending the JWT `Authorization` header when uploading images. The backend's `get_optional_user()` reads the token from the header only — no header meant no user, so scan history was never saved and dashboard counters stayed at zero. Fixed by attaching the token from Alpine's auth store.

**Welcome page accuracy**: The welcome page had hardcoded numbers (1,000 signs, 260 landmarks, 5 stories) that drifted from reality. Now dynamically pulled from actual data sources: 1,023 Gardiner signs, 260 heritage sites, 12 mythology stories.

**Wikimedia image reliability**: The landmark explorer loaded raw full-resolution Wikimedia URLs (5–20 MB each). With 24+ images loading concurrently and Alpine.js re-rendering the grid, the browser cancelled in-flight requests — causing NS_BINDING_ABORTED errors and broken images everywhere. All URLs now clamped to thumbnail size, with `decoding="async"` and `@error` fallbacks on every `<img>`.

**Camera tab**: Temporarily removed from both scan and explore pages after discovering cross-browser issues with `getUserMedia` — the video element was being destroyed and recreated by Alpine's `x-if`, causing black screens on mobile.

---

## Chapter 9: By The Numbers (Current)

| What | How Much |
|------|----------|
| Gardiner signs in dictionary | 1,023 |
| Egyptian heritage sites | 260+ |
| Interactive mythology stories | 12 |
| Hieroglyph recognition accuracy | 98.2% |
| Landmark recognition accuracy | 93.8% |
| Hieroglyph classes supported | 171 |
| Landmark sites recognized | 52 |
| Total model size (all three) | ~42 MB |
| Image URLs for landmarks | 1,220+ |
| AI providers in rotation | 4 (Gemini, Grok, Groq, Cloudflare) |
| TTS voices configured | 6 contexts |
| Translatable hieroglyphs | 88 |

---

## What's Next

The platform is live and deployed. Future plans include a deeper Egyptian translation engine, enhanced landmark experiences with multi-modal AI, camera-based scanning restoration, and continued improvements to detection accuracy.

**Try it**: [nadercr7-wadjet-v2.hf.space](https://nadercr7-wadjet-v2.hf.space)

---

*Built by Nader Mohamed*
