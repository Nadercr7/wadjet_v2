"""Full validation of Wadjet v2 — run after all changes."""
import ast
import json
import os
import sys
import urllib.request

BASE = "http://localhost:8333"
PASS = 0
FAIL = 0


def check(name, condition):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  OK  {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name}")


def fetch(path):
    return urllib.request.urlopen(BASE + path).read().decode()


print("=" * 60)
print("1. SYNTAX CHECK — all app/**/*.py")
print("=" * 60)
errors = []
for root, dirs, files in os.walk("app"):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            try:
                raw = open(path, "rb").read()
                if raw.startswith(b"\xef\xbb\xbf"):
                    raw = raw[3:]
                ast.parse(raw.decode("utf-8"))
            except SyntaxError as e:
                errors.append(f"{path}: {e}")
if errors:
    for e in errors:
        print(f"  FAIL {e}")
    FAIL += len(errors)
else:
    PASS += 1
    print("  OK  All Python files syntax valid")

print()
print("=" * 60)
print("2. ROUTE CHECKS — 9 routes return 200")
print("=" * 60)
routes = ["/api/health", "/", "/hieroglyphs", "/landmarks",
          "/scan", "/dictionary", "/write", "/explore", "/chat"]
for r in routes:
    try:
        status = urllib.request.urlopen(BASE + r).status
        check(f"{r} -> {status}", status == 200)
    except Exception as e:
        check(f"{r} -> ERROR: {e}", False)

print()
print("=" * 60)
print("3. DATA COUNTS")
print("=" * 60)
sites = json.load(open("data/expanded_sites.json", encoding="utf-8"))
top_level = [s for s in sites if not s.get("parent_slug")]
check(f"260 total sites (got {len(sites)})", len(sites) == 260)
check(f"161 top-level (got {len(top_level)})", len(top_level) == 161)

sys.path.insert(0, ".")
from app.core.gardiner import GARDINER_TRANSLITERATION
check(f"1023 Gardiner signs (got {len(GARDINER_TRANSLITERATION)})", len(GARDINER_TRANSLITERATION) == 1023)

cache = json.load(open("data/landmark_enrichment_cache.json", encoding="utf-8"))
check(f"Enrichment cache exists ({len(cache)} entries)", isinstance(cache, dict))

corpus = sum(1 for _ in open("data/translation/write_corpus.jsonl", encoding="utf-8"))
check(f"Write corpus: {corpus} entries (>14000)", corpus > 14000)

print()
print("=" * 60)
print("4. TEMPLATE NUMBER CHECKS")
print("=" * 60)
landing = fetch("/")
check("Landing: has 260+", "260+" in landing)
check("Landing: has 1,000+", "1,000+" in landing)
check("Landing: no stale 52", "52 Egyptian" not in landing)

landmarks = fetch("/landmarks")
check("Landmarks: has 260+", "260+" in landmarks)
lm_body = landmarks.split("</head>")[1] if "</head>" in landmarks else landmarks
check("Landmarks: no stale 52 in body", "52" not in lm_body.split("</footer>")[0] if "</footer>" in lm_body else True)

hieroglyphs = fetch("/hieroglyphs")
check("Hieroglyphs: has 1,000+", "1,000+" in hieroglyphs)
check("Hieroglyphs: no stale 700+", "700+" not in hieroglyphs)

print()
print("=" * 60)
print("5. CHAT FEATURES — TTS + STT + Groq fallback")
print("=" * 60)
chat_html = fetch("/chat")
check("Chat: TTS speakToggle", "WadjetTTS.speakToggle" in chat_html)
check("Chat: TTS poller", "_ttsPoller" in chat_html)
check("Chat: STT toggleRecording", "toggleRecording()" in chat_html)
check("Chat: Mic button", "Voice input" in chat_html)
check("Chat: /api/stt call", "/api/stt" in chat_html)
check("Chat: voiceText state", "voiceText" in chat_html)
check("Chat: clearChat stops TTS", "WadjetTTS.stop()" in chat_html)

# Backend checks
chat_py = open("app/api/chat.py", encoding="utf-8").read()
check("chat.py: _get_groq helper", "_get_groq" in chat_py)
check("chat.py: groq passed to stream", "groq=groq" in chat_py)

thoth = open("app/core/thoth_chat.py", encoding="utf-8").read()
check("thoth_chat: GroqService type hint", "GroqService" in thoth)
check("thoth_chat: 3-provider fallback", "Groq fallback" in thoth or "groq.generate_text" in thoth)

print()
print("=" * 60)
print("6. FALLBACK CHAIN CONSISTENCY")
print("=" * 60)
ai_svc = open("app/core/ai_service.py", encoding="utf-8").read()
check("GroqService.generate_text()", "async def generate_text(" in ai_svc)
check("GroqService.generate_text_stream()", "async def generate_text_stream(" in ai_svc)
check("GroqService.text_json()", "async def text_json(" in ai_svc)
check("GroqService.vision_json()", "async def vision_json(" in ai_svc)

explore = open("app/api/explore.py", encoding="utf-8").read()
check("Explore: _get_groq", "_get_groq" in explore)
check("Explore: _run_groq_vision", "_run_groq_vision" in explore)
check("Explore: enrichment cache", "_EnrichmentCache" in explore)

print()
print("=" * 60)
print("7. GIT STATUS")
print("=" * 60)
import subprocess
result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
lines = [l for l in result.stdout.strip().split("\n") if l.strip() and not l.strip().startswith("??")]
check("No uncommitted tracked changes", len(lines) == 0)
log = subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True)
check(f"HEAD: {log.stdout.strip()}", True)

print()
print("=" * 60)
total = PASS + FAIL
print(f"RESULTS: {PASS}/{total} passed, {FAIL} failed")
if FAIL == 0:
    print("ALL CHECKS PASSED")
else:
    print("SOME CHECKS FAILED")
print("=" * 60)
