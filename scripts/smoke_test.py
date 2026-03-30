"""Smoke test against running dev server (http://localhost:8000)."""
import httpx

base = "http://127.0.0.1:8001"
client = httpx.Client(timeout=30.0)
results = []

def check(desc, ok, detail=""):
    status = "PASS" if ok else "FAIL"
    results.append(f"  [{status}] {desc}" + (f" -- {detail}" if detail else ""))

# 5a: / is public (landing page)
r = client.get(f"{base}/", follow_redirects=False)
check("/ is public (200)", r.status_code == 200, f"{r.status_code}")

# 5b: /welcome -> 200 with sections
r = httpx.get(f"{base}/welcome", follow_redirects=True)
check("/welcome -> 200", r.status_code == 200)
check("/welcome has sign-up", "signup" in r.text.lower())
check("/welcome has brand-mark", "brand-mark" in r.text)
check("/welcome 5+ data-animate", r.text.count("data-animate") >= 5,
      f"{r.text.count('data-animate')} found")

# 5d: Protected routes -> redirect
for route in ["/scan", "/dictionary", "/write", "/chat", "/stories", "/dashboard", "/settings"]:
    r = httpx.get(f"{base}{route}", follow_redirects=False)
    check(f"{route} no cookie -> redirect", r.status_code == 302 and "/welcome" in r.headers.get("location", ""),
          f"{r.status_code}")

# 5e: /scan with cookie
r = httpx.get(f"{base}/scan", cookies={"wadjet_session": "1"}, follow_redirects=True)
check("/scan -> 200 with cookie", r.status_code == 200)
check("/scan: no detection_source badge", 'x-show="result.detection_source"' not in r.text)
check("/scan: no provider line", 'x-show="result.ai_reading?.provider"' not in r.text)

# 5f: /write smart-only
r = httpx.get(f"{base}/write", cookies={"wadjet_session": "1"}, follow_redirects=True)
check("/write -> 200", r.status_code == 200)
check("/write: no tablist toggle", 'role="tablist"' not in r.text)
check("/write: smart examples", "examples.smart" in r.text)
check("/write: smart subtitle rendered", "Type" in r.text or "hieroglyph" in r.text.lower())

# 5g: /chat TTS 3-state
r = httpx.get(f"{base}/chat", cookies={"wadjet_session": "1"}, follow_redirects=True)
check("/chat -> 200", r.status_code == 200)
check("/chat: 3-state TTS", "animate-spin" in r.text and "ttsState" in r.text)

# 5h: Arabic RTL
r = httpx.get(f"{base}/welcome?lang=ar", follow_redirects=True)
check("Arabic -> RTL", 'dir="rtl"' in r.text)

# 5i: stories + story reader
r = httpx.get(f"{base}/stories", cookies={"wadjet_session": "1"}, follow_redirects=True)
check("/stories -> 200", r.status_code == 200)

r = client.get(f"{base}/stories/contendings-horus-set", cookies={"wadjet_session": "1"}, follow_redirects=True)
check("/stories/{id} -> 200", r.status_code == 200)
check("Story: completion celebration", "showCompletion" in r.text)

# 5j: /api/health (public)
r = httpx.get(f"{base}/api/health", follow_redirects=False)
check("/api/health -> 200", r.status_code == 200)

# Security: open redirect prevention
r = httpx.get(f"{base}/welcome?next=https://evil.com", follow_redirects=True)
check("Open redirect blocked", 'href="https://evil.com"' not in r.text)

# Print results
print("\n" + "=" * 60)
print("  SMOKE TEST RESULTS")
print("=" * 60)
for line in results:
    print(line)
passed = sum(1 for r in results if "[PASS]" in r)
failed = sum(1 for r in results if "[FAIL]" in r)
print(f"\n  {passed} passed, {failed} failed out of {passed + failed}")
print("=" * 60)
