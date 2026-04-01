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

## Chapter 5: By The Numbers

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
| Interactive mythology stories | 13 |
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

## What's Next

The platform is live and deployed. Future plans include a deeper Egyptian translation engine, enhanced landmark experiences with multi-modal AI, and continued improvements to detection accuracy.

**Try it**: [nadercr7-wadjet-v2.hf.space](https://nadercr7-wadjet-v2.hf.space)

---

*Built by Nader Mohamed*
