# Wadjet v3 Beta — Constitution

> Immutable rules governing all v3 development. No phase may violate these.

## Identity

- **Project**: Wadjet — AI-powered Egyptian Heritage Explorer
- **Version**: v3.0.0-beta (SaaS transformation)
- **Goal**: Transform from a demo project into a production-ready SaaS product

## Locked Stack (Do Not Change)

| Layer | Technology | Version |
|-------|-----------|---------|
| Backend | FastAPI | latest |
| Templates | Jinja2 | — |
| Reactivity | Alpine.js | 3.14.x |
| Partial loading | HTMX | 2.0.x |
| CSS | TailwindCSS | v4.x |
| ML inference | ONNX Runtime | latest |
| AI providers | Gemini, Grok, Groq, Cloudflare Workers AI | free tiers |
| Python | 3.11+ | — |

## New Stack (SaaS Layer)

| Layer | Technology | Reason |
|-------|-----------|--------|
| Database | SQLite via aiosqlite (beta) → PostgreSQL (prod) | Zero cost, ships with Python |
| ORM | SQLAlchemy 2.0 async | Industry standard, PostgreSQL migration trivial |
| Migrations | Alembic | Schema versioning |
| Auth | JWT + bcrypt (custom) | No external dependency, patterns from minimal-fastapi-postgres-template |
| Rate limiting | slowapi | 3 lines to add |
| CSRF | starlette-csrf | Middleware, 2 lines |
| Gemini SDK | google-genai | TTS + image understanding (already use Gemini for chat) |
| HTTP client | httpx | Async calls to Cloudflare Workers AI |

## Design System

- **Colors**: Black (#0A0A0A) + Gold (#D4AF37)
- **Fonts**: Playfair Display (headings) + Inter (body) + Cairo (Arabic)
- **Dark mode only** — no light theme
- **Glass morphism** nav: `bg-night/80 backdrop-blur-xl`

## Development Rules

1. **Work on the copy only** — `Wadjet-v3-beta/`, never touch original `Wadjet/`
2. **Git commit after each phase** — descriptive message, tag with phase number
3. **No random train/test splits** — temporal splits only (if ML changes needed)
4. **No same-year features** — prevent data leakage
5. **Offline must work** — every change must preserve offline functionality
6. **All CDN scripts self-hosted** — no external runtime dependencies
7. **Arabic is first-class** — every UI string must have an Arabic translation
8. **WCAG AA minimum** — 4.5:1 contrast ratio, labels, ARIA attributes
9. **No breaking changes to existing API** — all endpoints must remain backward compatible
10. **Test after every phase** — no phase is complete without passing its test checklist

## Security Baseline

- All POST endpoints: CSRF token required
- All API endpoints: rate-limited (slowapi)
- File uploads: magic byte validation, not just content-type
- Error messages: generic to user, detailed to server logs
- No secrets in client-side code
- SRI on any remaining external scripts
- JWT tokens: short-lived (30min access, 7d refresh)
- Passwords: bcrypt with cost factor 12

## File Organization

```
app/
├── api/          # Route handlers (thin — delegate to core/)
├── core/         # Business logic, ML pipelines, AI services
├── db/           # NEW: models, schemas, crud, database.py
├── auth/         # NEW: JWT, password hashing, dependencies
├── templates/    # Jinja2 HTML
├── static/       # CSS, JS, fonts, vendor/, images
│   └── vendor/   # NEW: self-hosted CDN scripts
├── i18n/         # NEW: en.json, ar.json
└── utils/        # Helpers
```

## AI Generation Services (Smart Defaults)

> **Philosophy**: The system auto-selects the highest quality provider. The user never chooses — the system picks the best available, with graceful fallback. No provider selector in the UI.

### TTS / Narrative Voice (All Pages)

| Priority | Provider | Model | Languages | Notes |
|----------|----------|-------|-----------|-------|
| 1 (Primary) | **Gemini API** | `gemini-2.5-flash-preview-tts` | 73+ langs (ar, en, etc.) | FREE on free tier. 30 voices, style-controllable via director's notes. Best quality. |
| 2 (Fallback) | **Groq** | Orpheus v1 English + Orpheus Arabic Saudi | en, ar | FREE. Expressive with vocal directions `[cheerful]`, `[sad]`. Already integrated. |
| 3 (Offline) | **Browser** | SpeechSynthesis API | varies | Always available offline. Lowest quality. |

**Gemini TTS voice recommendations:**
- English narrative: `Charon` (Informative) or `Rasalgethi` (Informative)
- Arabic narrative: `Sulafat` (Warm) or `Sadaltager` (Knowledgeable)
- Story narration: `Aoede` (Breezy) for myths, `Kore` (Firm) for descriptions
- Chat (Thoth): `Orus` (Firm) — authoritative ancient voice

### Image Generation (Stories)

| Priority | Provider | Model | Notes |
|----------|----------|-------|-------|
| 1 (Primary) | **Cloudflare Workers AI** | `@cf/black-forest-labs/FLUX-1-schnell` | FREE, fastest, good quality |
| 2 (Fallback) | **Cloudflare Workers AI** | `@cf/stabilityai/stable-diffusion-xl-base-1.0` | FREE, more detailed |
| 3 (Last resort) | **Static** | Pre-made placeholder illustrations | Ships with app, always works |

### Video Generation

No free API available. Use **CSS/Canvas animations on AI-generated images**:
- Ken Burns effect (slow zoom + pan on static images)
- Parallax scrolling (foreground/background layers)
- Fade transitions between story scenes
- This provides a "cinematic" feel without actual video generation

### Fallback Chain Logic
```python
# Smart defaults pattern — used throughout the app
async def generate_with_fallback(providers: list, *args, **kwargs):
    for provider in providers:
        try:
            result = await provider.generate(*args, **kwargs)
            if result:
                return result
        except Exception as e:
            logger.warning(f"{provider.name} failed: {e}")
    return None  # All providers failed, UI shows graceful degradation
```

## Development Rules (UPDATED)

> Rule 11 added.

11. **Smart defaults everywhere** — system picks the best AI provider automatically, user has no provider selector. Graceful fallback chain: best → good → offline. Applies to TTS, image gen, chat AI, and all AI features.

## Out of Scope for Beta

- Payment processing (Stripe) — marked as "coming soon"
- Email system (Resend/Postmark) — not needed yet
- Full admin dashboard — basic stats only
- CDN/edge deployment — single server is fine
- Mobile native app — PWA only
- AR features — requires native capabilities
- **Video generation** — no free API, use image animations instead
- **Music generation** — Lyria 3 is paid, use royalty-free ambient audio
