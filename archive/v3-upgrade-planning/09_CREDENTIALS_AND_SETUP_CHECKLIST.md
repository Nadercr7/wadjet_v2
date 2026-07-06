# CREDENTIALS & SETUP CHECKLIST — Phase 0 (Do This First)

> This is the FIRST phase. Complete every item before writing any code.  
> Most items require USER ACTION (account dashboards, copy-paste).

---

## Status Legend

- ⬜ Not started
- 🟡 In progress
- ✅ Done

---

## Section 1: Existing Environment Variables (Verify)

These are already in `.env`. Verify each one works.

| # | Variable | Status | How to Verify |
|---|----------|--------|--------------|
| 1.1 | `GEMINI_API_KEYS` (17 keys) | ⬜ | `curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=KEY" -H "Content-Type: application/json" -d '{"contents":[{"parts":[{"text":"hi"}]}]}'` → should return response |
| 1.2 | `GEMINI_MODEL` | ⬜ | Value should be `gemini-2.5-flash` |
| 1.3 | `GEMINI_LITE_MODEL` | ⬜ | Value should be `gemini-2.5-flash-lite` |
| 1.4 | `GEMINI_EMBEDDING_MODEL` | ⬜ | Value should be `gemini-embedding-001` |
| 1.5 | `GROK_API_KEYS` (8 keys) | ⬜ | Test one key against `https://api.x.ai/v1/chat/completions` |
| 1.6 | `GROK_MODEL` | ⬜ | Value should be `grok-4-latest` |
| 1.7 | `GROQ_API_KEYS` (8 keys) | ⬜ | Test one key against `https://api.groq.com/openai/v1/chat/completions` |
| 1.8 | `CLOUDFLARE_ACCOUNT_ID` | ⬜ | Check at https://dash.cloudflare.com → right sidebar |
| 1.9 | `CLOUDFLARE_API_TOKEN` | ⬜ | Test: `curl -X POST "https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai/run/@cf/black-forest-labs/FLUX-1-schnell" -H "Authorization: Bearer TOKEN" -H "Content-Type: application/json" -d '{"prompt":"test"}'` |
| 1.10 | `GOOGLE_CLIENT_ID` | ⬜ | Should end in `.apps.googleusercontent.com` |
| 1.11 | `RESEND_API_KEY` | ⬜ | Test: `curl -X POST "https://api.resend.com/emails" -H "Authorization: Bearer KEY" -H "Content-Type: application/json" -d '{"from":"onboarding@resend.dev","to":"naderelakany@gmail.com","subject":"test","text":"hello"}'` |
| 1.12 | `HF_TOKEN` | ⬜ | Test: `curl -H "Authorization: Bearer TOKEN" https://huggingface.co/api/whoami` |

---

## Section 2: Missing Environment Variables (Add)

These are NOT in `.env` yet. You need to add them.

### 2.1 `GOOGLE_CLIENT_SECRET` ⬜

**Where to get it**:
1. Go to https://console.cloud.google.com/apis/credentials
2. Click on the OAuth 2.0 Client ID that matches your `GOOGLE_CLIENT_ID`
3. Copy the **Client Secret** value
4. Add to `.env`:
   ```
   GOOGLE_CLIENT_SECRET=your_secret_here
   ```

**While you're there, also verify**:
- ✅ Authorized JavaScript origins includes `http://localhost:8000`
- ✅ Authorized JavaScript origins includes `https://nadercr7-wadjet-v2.hf.space`
- ✅ Authorized redirect URIs includes `http://localhost:8000`
- ✅ Authorized redirect URIs includes `https://nadercr7-wadjet-v2.hf.space`
- ✅ Consent screen has app name "Wadjet"
- ✅ Scopes include: `email`, `profile`, `openid`

### 2.2 `JWT_SECRET` ⬜

**How to generate**:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Add to `.env`:
```
JWT_SECRET=<paste the 64-character hex string>
```

⚠ This MUST be the same on every deployment. If it changes, all users are logged out.

### 2.3 `CSRF_SECRET` ⬜

**How to generate**:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Add to `.env`:
```
CSRF_SECRET=<paste a DIFFERENT 64-character hex string>
```

### 2.4 `ENVIRONMENT` ⬜

For local development:
```
ENVIRONMENT=development
```

For HuggingFace Space (set in Space Settings):
```
ENVIRONMENT=production
```

### 2.5 `BASE_URL` ⬜

For local development:
```
BASE_URL=http://localhost:8000
```

For production:
```
BASE_URL=https://nadercr7-wadjet-v2.hf.space
```

---

## Section 3: Code Changes Required (AI Will Do)

These changes will be made by the AI assistant after you complete Sections 1-2.

| # | Change | File | Description |
|---|--------|------|-------------|
| 3.1 | Add `google_client_secret` field | `app/config.py` | `google_client_secret: str = ""` |
| 3.2 | Create `.env.example` | Project root | All variable names with descriptions |
| 3.3 | Fix classifier path default | `app/config.py` | Point to uint8 model |
| 3.4 | Fix BASE_URL default | `app/config.py` | Change from render.com to HF Space |

---

## Section 4: External Service Configuration

### 4.1 Google Cloud Console — OAuth Setup ⬜

1. Go to https://console.cloud.google.com/apis/credentials
2. Select your OAuth 2.0 Client ID
3. **Authorized JavaScript Origins** — add:
   ```
   http://localhost:8000
   https://nadercr7-wadjet-v2.hf.space
   ```
4. **Authorized Redirect URIs** — add:
   ```
   http://localhost:8000
   https://nadercr7-wadjet-v2.hf.space
   ```
5. Save
6. Go to **OAuth Consent Screen**:
   - App name: `Wadjet`
   - User support email: `naderelakany@gmail.com`
   - Developer contact: `naderelakany@gmail.com`
   - Authorized domains: Add `hf.space`
   - Save

### 4.2 Resend — Email Sending Setup ⬜

1. Go to https://resend.com/domains
2. Check if a sending domain is configured
   - **If yes**: Note the domain name (e.g., `yourdomain.com`)
   - **If no**: Use `onboarding@resend.dev` for testing (100 emails/day limit)
3. Go to https://resend.com/api-keys → verify key matches `.env`

**Questions to answer**:
- What domain will you send from? `______________`
- Or use `onboarding@resend.dev` for now? `yes / no`

### 4.3 HuggingFace Space — Environment Variables ⬜

> Do this LATER during Phase 5 (Promotion). Just verify access now.

1. Go to https://huggingface.co/spaces/nadercr7/wadjet-v2/settings
2. Verify you can access the Settings page
3. Note: Secrets are encrypted and hidden after saving

---

## Section 5: Database Decision ⬜

Choose one:

### Option A: SQLite (Default, Ephemeral on HF)
- **Pro**: Works immediately, no external services
- **Con**: Data wiped when HF Space rebuilds (sleep, update, crash)
- **Best for**: Development, demos, MVP
- **Config**: No change needed (default)

### Option B: Supabase PostgreSQL (Persistent)
- **Pro**: Data persists across deployments
- **Con**: External dependency, setup time
- **Best for**: Production with real users
- **Setup**:
  1. Go to https://supabase.com → New Project
  2. Choose free tier (500MB, 2 projects max)
  3. Copy connection string from Settings → Database → URI
  4. Add to `.env`: `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/dbname`
  5. Add `asyncpg` to `requirements.txt`

**Your decision**: `SQLite / Supabase`

---

## Section 6: Git Remotes ⬜

Currently, v3-beta has NO git remotes. Verify you have push access:

1. Check GitHub access:
   ```bash
   # Test SSH (if using SSH)
   ssh -T git@github.com
   
   # Or test HTTPS (if using token)
   curl -H "Authorization: token YOUR_GITHUB_TOKEN" https://api.github.com/user
   ```

2. Check HuggingFace access:
   ```bash
   curl -H "Authorization: Bearer YOUR_HF_TOKEN" https://huggingface.co/api/whoami
   ```

3. Decide auth method:
   - **SSH**: `git@github.com:Nadercr7/wadjet_v2.git`
   - **HTTPS**: `https://github.com/Nadercr7/wadjet_v2.git` (needs credential manager or token)

4. Decide HF push method:
   - **HTTPS with token**: `https://nadercr7:HF_TOKEN@huggingface.co/spaces/nadercr7/wadjet-v2`

---

## Section 7: Security Token Rotation ⬜

The old Wadjet repo has an HF token embedded in `.git/config`. After promotion:

1. Go to https://huggingface.co/settings/tokens
2. Revoke the old token
3. Create a new token with write access to `nadercr7/wadjet-v2`
4. Update `.env` with new `HF_TOKEN`
5. Update HF Space settings with new token

---

## Section 8: Local Development Test ⬜

After completing Sections 1-3, run this verification:

```bash
cd "D:\Personal attachements\Projects\Wadjet-v3-beta"
.venv\Scripts\activate

# 1. Verify Python
python --version  # Should be 3.13

# 2. Install any new dependencies
pip install -r requirements.txt

# 3. Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Test endpoints
# In another terminal:
curl http://localhost:8000/api/health
# Expected: {"status":"ok",...}

curl http://localhost:8000/
# Expected: HTML landing page

# 5. Run tests
pytest tests/ -v --tb=short
```

---

## Summary Checklist

| Section | Items | Your Status |
|---------|-------|-------------|
| 1. Existing env vars | 12 to verify | ⬜ |
| 2. Missing env vars | 5 to add | ⬜ |
| 3. Code changes | 4 changes (AI does) | ⬜ |
| 4. External services | 3 services to configure | ⬜ |
| 5. Database decision | 1 decision | ⬜ |
| 6. Git remotes | Verify access | ⬜ |
| 7. Token rotation | Schedule for after promotion | ⬜ |
| 8. Local dev test | Run smoke test | ⬜ |

**When all ✅, tell the AI: "Phase 0 complete, start Phase 1 (Security Audit)"**
