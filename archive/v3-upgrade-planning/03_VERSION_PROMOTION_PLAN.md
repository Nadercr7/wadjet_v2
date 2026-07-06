# VERSION PROMOTION PLAN — v3-beta → Production

> Covers: Git strategy, HF deployment, environment migration, archive of v2, CHANGELOG.

---

## Current State

### v3-beta Repository
```
Path:     D:\Personal attachements\Projects\Wadjet-v3-beta
Branch:   master
Remotes:  NONE (local only)
Tag:      v3.0.0-beta
Commit:   23d96de "fix(security): restrict feedback admin to naderelakany@gmail.com only"
```

### Old Wadjet Repository (v2, live on HF)
```
Path:     D:\Personal attachements\Projects\Wadjet
Branch:   clean-main (default)
Remotes:  origin → github.com/Nadercr7/wadjet_v2
          hf     → huggingface.co/spaces/nadercr7/wadjet-v2
Commit:   79bfabe "fix: restore .dockerignore"
⚠ HF token embedded in .git/config (security risk)
```

### HuggingFace Space
```
URL:      https://huggingface.co/spaces/nadercr7/wadjet-v2
SDK:      Docker
Port:     7860
Status:   Sleeping (inactive)
```

---

## Promotion Steps (Ordered)

### Step 1: Archive v2

On the **Old Wadjet** repository:

```bash
cd "D:\Personal attachements\Projects\Wadjet"
git tag -a v2.0.0-archive -m "Archive: Wadjet v2 final state before v3 promotion"
git push origin v2.0.0-archive
```

### Step 2: Prepare v3-beta for Push

On **v3-beta**:

```bash
cd "D:\Personal attachements\Projects\Wadjet-v3-beta"

# Add remotes
git remote add origin https://github.com/Nadercr7/wadjet_v2.git
git remote add hf https://huggingface.co/spaces/nadercr7/wadjet-v2

# Rename branch to main (optional, can stay master)
# git branch -m master main

# Verify
git remote -v
git log --oneline -5
```

### Step 3: Fix Dockerfile for HF Space

Current issues:
- Port is 8000, HF expects 7860
- Need to verify all layers are correct

```dockerfile
# In Dockerfile, change:
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
```

### Step 4: Update Config Defaults

In `app/config.py`:
```python
base_url: str = "https://nadercr7-wadjet-v2.hf.space"
port: int = 7860  # HF Space port
```

### Step 5: Set HF Space Environment Variables

Go to: https://huggingface.co/spaces/nadercr7/wadjet-v2/settings

Set these variables (Secrets, not public):

| Variable | Value | Notes |
|----------|-------|-------|
| `ENVIRONMENT` | `production` | Enforces secret validation |
| `JWT_SECRET` | `<64-char hex>` | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `CSRF_SECRET` | `<64-char hex>` | Same generation method |
| `GEMINI_API_KEYS` | `key1,key2,...` | All 17 keys, comma-separated |
| `GROK_API_KEYS` | `key1,key2,...` | All 8 keys |
| `GROQ_API_KEYS` | `key1,key2,...` | All 8 keys |
| `CLOUDFLARE_ACCOUNT_ID` | `<value>` | |
| `CLOUDFLARE_API_TOKEN` | `<value>` | |
| `GOOGLE_CLIENT_ID` | `<value>` | |
| `GOOGLE_CLIENT_SECRET` | `<value>` | |
| `RESEND_API_KEY` | `<value>` | |
| `HF_TOKEN` | `<value>` | Rotated token (not the one in old .git/config) |
| `DATABASE_URL` | `sqlite+aiosqlite:///data/wadjet.db` | Or PostgreSQL if decided |

### Step 6: Push Code

```bash
# Push to GitHub
git push -u origin master

# Push to HuggingFace (triggers rebuild)
git push hf master:main
```

### Step 7: Verify Deployment

1. Wait for HF build to complete (check build logs)
2. Visit https://nadercr7-wadjet-v2.hf.space
3. Test all routes:
   - `/` — Landing page loads
   - `/hieroglyphs` — Hub page
   - `/scan` — Scanner loads (camera/upload)
   - `/dictionary` — Dictionary loads
   - `/explore` — Landmarks load
   - `/stories` — Stories list
   - `/chat` — Thoth chat responds
   - `/dashboard` — Auth required → redirect to login
4. Test auth:
   - Register new user
   - Login with email/password
   - Google Sign-In
   - Logout
5. Test core features:
   - Scan an image → get results
   - Read a story → images load, TTS works
   - Chat with Thoth → streaming response

### Step 8: Tag Release

```bash
git tag -a v3.0.0 -m "Wadjet v3.0.0: Production release with OAuth, enriched stories, upgraded scan pipeline"
git push origin v3.0.0
git push hf v3.0.0
```

### Step 9: Security Cleanup

1. Rotate HF token (old one is in Wadjet/.git/config)
2. Update HF Space with new token
3. Consider making old Wadjet repo private or adding redirect notice

---

## CHANGELOG.md Template

```markdown
# Changelog

## [3.0.0] — 2026-XX-XX

### Added
- Google OAuth sign-in (one-tap + button)
- Email verification via Resend
- Password reset via email
- 5 historically accurate Egyptian mythology stories
- Story narration via Gemini TTS (3-tier fallback)
- AI-generated story illustrations (Cloudflare FLUX.1)
- Interactive story elements (quizzes, choices)
- Scan result TTS narration
- Step-by-step scan progress UI
- W-serpent animated logo
- Page loading animation
- Comprehensive security headers (CSP, HSTS, etc.)
- .env.example template

### Changed
- Auth: JWT secrets are now required (not auto-generated) in production
- Scan: classifier defaults to uint8 quantized model
- Config: BASE_URL defaults to HF Space URL
- Docker: port changed from 8000 to 7860 for HF Space
- Stories: rewritten with real Egyptian history sources

### Fixed
- Token refresh race condition in client JS
- TTS service disconnected from /api/tts endpoint
- docker-compose data/ mount (ro → rw)
- File upload validation (magic bytes + extension)
- Error responses no longer leak stack traces

### Security
- Fixed JWT_SECRET auto-generation vulnerability
- Added CSP, X-Frame-Options, X-Content-Type-Options headers
- Added file upload magic byte validation
- Password minimum complexity (8+ chars)
- Rate limiting on all auth endpoints

## [3.0.0-beta] — 2026-03-29

### Notes
- Initial v3 development build
- Full rewrite from v2 (Flask → FastAPI)
- Added: auth system, database, dashboard, stories, feedback
```

---

## Database Considerations

### Option A: Keep SQLite (Simple, Ephemeral)
- **Pro**: Zero setup, works immediately
- **Con**: Data lost on HF Space rebuild (cold start, updates)
- **Mitigation**: Acceptable for MVP; users re-register after rebuild
- **Config**: `DATABASE_URL=sqlite+aiosqlite:///data/wadjet.db`

### Option B: Supabase PostgreSQL (Persistent)
- **Pro**: Data survives rebuilds, real database
- **Con**: External dependency, connection string management
- **Setup**: 
  1. Create Supabase project (free tier: 500MB, 2 projects)
  2. Get connection string from Settings → Database
  3. Set `DATABASE_URL=postgresql+asyncpg://...` 
  4. Add `asyncpg` to requirements.txt
  5. Run Alembic migrations against PostgreSQL
- **Config**: `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname`

### Recommendation
Start with **Option A** (SQLite) for initial promotion. Add PostgreSQL in a follow-up phase when user data persistence becomes critical. The SQLAlchemy async setup already supports both backends.

---

## Rollback Plan

If v3 deployment fails:

1. On HF Space, go to Settings → Factory Reset (or revert to previous commit)
2. Push v2 code back: `git push hf v2.0.0-archive:main --force` (exceptional case)
3. Verify v2 is running again
4. Debug v3 locally, fix, re-push
