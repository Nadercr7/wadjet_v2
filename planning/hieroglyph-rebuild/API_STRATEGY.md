# Wadjet v2 — Multi-API Strategy

> How we use 5+ AI providers for maximum reliability, zero cost, and high quality.

---

## Provider Inventory

### 1. Google Gemini (PRIMARY)
| Key | Value |
|-----|-------|
| Keys | 17 API keys (rotation) |
| Models | gemini-2.0-flash, gemini-2.5-flash-preview, gemini-2.5-pro-preview |
| Vision | ✅ Yes — best for hieroglyph reading |
| Embedding | text-embedding-004 (768-dim) |
| Generation | Excellent for translation + chat |
| Rate Limit | 15 RPM per key × 17 = 255 RPM effective |
| Cost | Free tier (generous) |
| Use For | Vision reading, translation, embedding, Thoth chat |

### 2. Groq (SECONDARY)
| Key | Value |
|-----|-------|
| Keys | 1 API key (free tier) |
| Models | llama-3.3-70b-versatile, meta-llama/llama-4-scout-17b-16e-instruct |
| Vision | ✅ Yes — Llama 4 Scout (vision capable) |
| STT | whisper-large-v3-turbo |
| TTS | playai-tts, playai-tts-arabic |
| Rate Limit | 30 RPM, 1000 req/day, 100K tokens/day |
| Cost | Free |
| Use For | Vision fallback, TTS, STT, translation fallback |

### 3. xAI Grok (TIEBREAKER)
| Key | Value |
|-----|-------|
| Keys | 8 API keys (rotation) |
| Models | grok-4-latest |
| Vision | ✅ Yes |
| Rate Limit | ~60 RPM per key × 8 = high throughput |
| Cost | Free tier (limited monthly credits) |
| Use For | Tiebreaker when Gemini & ONNX disagree, cross-validation |

### 4. Cohere (EMBEDDING/RAG)
| Key | Value |
|-----|-------|
| Keys | 1 API key (trial) |
| Embedding | embed-multilingual-v3.0 (1024-dim, 100+ languages) |
| Rerank | rerank-v3.5 |
| Generation | command-a-08-2025 |
| Rate Limit | 1000 API calls/month (trial), 10K/month (production) |
| Cost | Free trial |
| Use For | RAG embedding (better multilingual than MiniLM), reranking retrieved examples |

### 5. OpenRouter (EMERGENCY)
| Key | Value |
|-----|-------|
| Keys | 1 API key |
| Models | 29+ free models including Llama 3.1 8B, DeepSeek-V3, Qwen |
| Vision | ❌ No free vision models |
| Rate Limit | Varies per model, generally low |
| Cost | Free for select models |
| Use For | Emergency text fallback when all other providers are down |

### 6. Cloudflare Workers AI (FREE BONUS)
| Key | Value |
|-----|-------|
| Keys | 1 account (free) |
| Free Tier | 10,000 neurons/day **forever** — no expiry |
| Vision | ✅ Llama-3.2-11B-Vision, Mistral Small 3.1-24B, Llama 4 Scout, Gemma 3 12B |
| STT | Whisper large-v3-turbo |
| TTS | MeloTTS (multilingual) |
| Embeddings | bge-m3 (multilingual), EmbeddingGemma-300M |
| API Format | Custom REST (via Workers or direct API w/ account ID + token) |
| Use For | All-in-one secondary platform: vision, STT, TTS, embeddings |

### 7. Voyage AI (EMBEDDING POWERHOUSE)
| Key | Value |
|-----|-------|
| Keys | 1 API key (free signup) |
| Free Tier | **200 million tokens lifetime** + 150B pixels free |
| Models | voyage-4-large, voyage-multimodal-3.5 (text + images!) |
| Rerankers | rerank-2.5, rerank-2.5-lite — 200M tokens free |
| API Format | OpenAI-compatible |
| Use For | **Best for RAG**: embed MdC strings + hieroglyph images in unified vector space |

### 8. Google Cloud TTS (ARABIC TTS)
| Key | Value |
|-----|-------|
| Free Tier | **4 million chars/month** (Standard/WaveNet), 1M chars (Neural2) — perpetual |
| Languages | Arabic (`ar-XA` Neural), English, 40+ languages |
| API Format | Custom REST / gRPC |
| Use For | High-quality Arabic TTS for translation readback (4M chars/month is huge) |

### 9. ElevenLabs (PREMIUM TTS)
| Key | Value |
|-----|-------|
| Free Tier | 10,000 credits/month (~10 min multilingual v2 audio) |
| Languages | Arabic ✅, English ✅ |
| Quality | Highest quality AI TTS available |
| Use For | Optional premium voice for Thoth responses or landmark narrations |

### 10. Deepgram (STT + TTS)
| Key | Value |
|-----|-------|
| Free Tier | **$200 credit on signup** (~430 hours STT, or ~6.6M chars TTS) — no expiry |
| STT | Nova-3 — Arabic + English, diarization, formatting |
| TTS | Aura-2 — mainly English |
| Use For | Voice queries to Thoth, voice search for dictionary |

### 11. TLA (Thesaurus Linguae Aegyptiae) — EGYPTOLOGY API
| Key | Value |
|-----|-------|
| URL | `https://api.thesaurus-linguae-aegyptiae.de/` |
| Free Tier | Free, no API key needed |
| What | ~90,000 ancient Egyptian lemmas with transliteration, translation, attestations |
| Use For | Ground Thoth's answers in scholarly data, dictionary enrichment |

---

## Fallback Chains

### Vision Reading (hieroglyph inscription)
```
1. Gemini Flash/Pro (best quality, 17 keys)
   ↓ if rate-limited or error
2. Groq Llama 4 Scout (good quality, fast, free)
   ↓ if rate-limited or error
3. Grok (acceptable quality, 8 keys)
   ↓ if rate-limited or error
4. Cloudflare Workers AI — Llama-3.2-Vision / Mistral Small 3.1 (free daily)
   ↓ if all APIs down
5. ONNX pipeline only (lowest quality, always available)
```

### Translation (MdC → EN + AR)
```
1. Gemini Flash with RAG few-shot examples
   ↓ if rate-limited
2. Groq Llama 3.3 70B with same prompt
   ↓ if rate-limited
3. OpenRouter free model with same prompt
   ↓ if all APIs down
4. RAG-only (nearest corpus match, no generation)
```

### Embedding (for RAG)
```
Option A: Voyage AI voyage-4-large (200M tokens lifetime FREE, OpenAI-compatible) ⭐ BEST
Option B: Voyage AI voyage-multimodal-3.5 (embed images + text in same space!)
Option C: Gemini text-embedding-004 (768-dim, free, unlimited)
Option D: Cohere embed-multilingual-v3.0 (1024-dim, 1000/month trial)
Option E: Cloudflare bge-m3 (multilingual, 10K neurons/day)

Decision: Use Voyage AI — 200M free tokens is enormous, high quality, OpenAI-compatible
Voyage multimodal: Can embed hieroglyph crop images alongside MdC text for unified search
Voyage rerank-2.5: 200M free tokens for reranking retrieved → few-shot examples
Gemini backup: If Voyage exhausted, fall back to Gemini embedding
```

### TTS (Text-to-Speech)
```
1. Web Speech API (client-side, free, offline, decent quality)
   ↓ if user wants better Arabic quality
2. Google Cloud TTS (4M chars/month free, Arabic Neural voices ✅)
   ↓ if rate-limited
3. Groq PlayAI TTS (server-side, high quality, Arabic)
   ↓ if Groq down
4. Cloudflare MeloTTS (10K neurons/day free)
   ↓ if all APIs down
5. Fall back to Web Speech API
```

### STT (Speech-to-Text)
```
1. Groq Whisper Large V3 Turbo (free, fast)
   ↓ if Groq down
2. Deepgram Nova-3 ($200 credit, ~430 hrs, Arabic+English)
   ↓ if credit exhausted
3. Cloudflare Whisper (10K neurons/day)
   ↓ if all down
4. Web Speech API (browser native, less accurate)
```

### Thoth Chat
```
1. Gemini Flash (current, works well)
   ↓ if rate-limited
2. Groq Llama 3.3 70B
   ↓ if rate-limited
3. Cloudflare Workers AI (Llama 3.3 70B, free daily)
   ↓ if rate-limited
4. OpenRouter free model
```

---

## Key Rotation Strategy

### Gemini (17 keys)
```python
class GeminiKeyRotator:
    # Round-robin across 17 keys
    # Track per-key:
    #   - last_used_at
    #   - requests_this_minute
    #   - total_requests_today
    #   - is_rate_limited (with expire time)
    #
    # Selection algorithm:
    # 1. Filter out rate-limited keys
    # 2. Pick key with lowest requests_this_minute
    # 3. If tie, pick key with oldest last_used_at
    #
    # On 429 response:
    # Mark key as rate-limited for 60 seconds
    # Immediately try next key (no sleep)
```

### Grok (8 keys)
```python
class GrokKeyRotator:
    # Same algorithm as Gemini
    # Map to different base URLs if needed
```

### Single-key providers (Groq, Cohere, OpenRouter)
```python
# Simple rate tracking
# On 429: wait and retry once, then move to next provider
```

---

## API Configuration

### .env additions
```env
# Existing
GEMINI_API_KEY_1=...
...
GEMINI_API_KEY_17=...
GROK_API_KEY_1=...
...
GROK_API_KEY_8=...

# New
GROQ_API_KEY=gsk_...
COHERE_API_KEY=...
OPENROUTER_API_KEY=sk-or-v1-...
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_TOKEN=...
VOYAGE_API_KEY=pa-...
GOOGLE_CLOUD_TTS_API_KEY=...  # or use service account JSON
ELEVENLABS_API_KEY=...
DEEPGRAM_API_KEY=...
```

### config.py additions
```python
# Groq
groq_api_key: str = ""
groq_base_url: str = "https://api.groq.com/openai/v1"

# Cohere
cohere_api_key: str = ""

# OpenRouter
openrouter_api_key: str = ""
openrouter_base_url: str = "https://openrouter.ai/api/v1"

# Cloudflare Workers AI
cloudflare_account_id: str = ""
cloudflare_api_token: str = ""

# Voyage AI (embeddings)
voyage_api_key: str = ""

# Google Cloud TTS (optional, 4M chars/month free Arabic)
google_tts_api_key: str = ""

# AI Reader settings
ai_reader_mode: str = "auto"  # "auto", "ai", "onnx"
ai_reader_timeout: int = 10  # seconds per provider attempt
```

---

## Request Budget (Daily)

| Provider | Daily Budget | Per Scan | Max Scans/Day |
|----------|------------|----------|---------------|
| Gemini | ~3,825 RPD (17 × 225) | 1-2 calls | ~2,000 |
| Groq | 1,000 RPD | 1 call (fallback) | 1,000 |
| Grok | ~1,000+ RPD (8 keys) | 1 call (tiebreaker) | 1,000 |
| Cloudflare | 10,000 neurons/day | 1 call (fallback) | ~500 |
| Cohere | ~33 RPD (1000/month) | 0-1 (rerank) | 33 |
| Voyage AI | ~∞ (200M tokens lifetime) | 1 embed call | ~∞ |
| OpenRouter | ~100 RPD (varies) | 0-1 (emergency) | 100 |

**Effective capacity**: ~2,000+ scans/day with full AI reading. More than enough for a portfolio project.

---

## Error Handling

### Retry Policy
```
- First attempt: Primary provider
- On 429/500/timeout: Immediately try next provider (no backoff)
- On all providers failed: Return ONNX-only result with warning
- Never block the user — always return something
```

### Circuit Breaker
```
- If provider fails 5 consecutive times: mark as "unhealthy" for 5 minutes
- Don't waste time trying unhealthy providers
- Auto-recover after cooldown period
```

### Graceful Degradation
```
All APIs working → Full AI reading + translation + cross-validation
Gemini down      → Groq vision + Groq translation
Groq also down   → Grok vision + ONNX translation
All APIs down    → ONNX detect + classify + transliteration only
Offline mode     → Client-side ONNX + Web Speech TTS
```

---

## Security Considerations

1. **API keys in .env only** — never in code, templates, or client JS
2. **Server-side API calls only** — client never sees API keys
3. **Rate limit per user session** — prevent abuse (max 30 scans/hour per IP)
4. **Image validation** — check file type, size limits (10MB max), sanitize
5. **Response validation** — parse AI JSON responses defensively
6. **No API key rotation in client** — all rotation happens server-side

---

## Feature-Specific API Usage

### Write Feature (Phase W-WRITE)
```
Smart mode EN→Hieroglyphs:
1. Check known phrase shortcuts (instant, no API call) ← NEW
2. Gemini Flash with few-shot examples from write_corpus.jsonl
   ↓ if rate-limited
3. Groq Llama 3.3 70B with same prompt
   ↓ if rate-limited
4. Grok with same prompt
   ↓ if all APIs down
5. MdC parse if input looks like transliteration, else alpha mode
```

### Landmarks Identify (Phase L-LANDMARKS)
```
Current:  ONNX + Gemini parallel → Grok tiebreaker → best confidence
Improved: ONNX + Gemini parallel → Groq fallback → Grok tiebreaker → Cloudflare → ONNX-only

Identify fallback chain:
1. ONNX (always runs, 52 classes, local inference)
   + IN PARALLEL:
2. Gemini Vision (best quality, 17 keys)
   ↓ if rate-limited or error
3. Groq Llama 4 Scout (good quality, vision capable, free) ← NEW
   ↓ if rate-limited or error
4. Grok Vision (8 keys) ← currently tiebreaker only, promote to full fallback
   ↓ if rate-limited or error
5. Cloudflare Workers AI Vision (10K neurons/day free) ← NEW
   ↓ if all APIs down
6. ONNX-only result (always available, offline capable)
```

### Landmarks Detail Enrichment (Phase L-LANDMARKS)
```
For non-curated sites with empty fields:
1. Gemini Flash text generation (describe, highlights, visiting tips)
2. Cache in memory (LRU) or companion JSON file
3. TLA API for pharaonic sites: scholarly lemma data (free, no key)
```
