"""Test landmark identification pipeline — services, ensemble, fallback chain, endpoint.

Run:  python scripts/test_identify.py
Requires: server running at http://localhost:8000 (for live tests)

Tests:
  1. Service import & initialization
  2. Ensemble merge logic
  3. CloudflareService structure
  4. TLAService structure
  5. Live endpoint — happy path (if server running)
  6. Live endpoint — not-Egyptian detection (if server running)
  7. Fallback chain wiring check
"""

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0


def log_result(name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def test_service_imports():
    """Test 1: All services import without error."""
    print("\n── Test 1: Service Imports ──")
    services = [
        ("app.core.cloudflare_service", "CloudflareService"),
        ("app.core.tla_service", "TLAService"),
        ("app.core.ai_service", "GroqService"),
        ("app.core.grok_service", "GrokService"),
        ("app.core.gemini_service", "GeminiService"),
        ("app.core.ensemble", "Candidate"),
        ("app.core.ensemble", "merge_landmark"),
        ("app.core.landmark_pipeline", "LandmarkPipeline"),
    ]
    for module_name, class_name in services:
        try:
            mod = __import__(module_name, fromlist=[class_name])
            getattr(mod, class_name)
            log_result(f"import {module_name}.{class_name}", True)
        except Exception as e:
            log_result(f"import {module_name}.{class_name}", False, str(e))


def test_ensemble_merge():
    """Test 2: Ensemble merge logic produces correct results."""
    print("\n── Test 2: Ensemble Merge Logic ──")
    from app.core.ensemble import Candidate, merge_landmark

    # Agreement: ONNX + Gemini agree
    onnx = Candidate(slug="pyramids_of_giza", name="Pyramids of Giza", confidence=0.85, source="onnx")
    gemini = Candidate(slug="pyramids_of_giza", name="Great Pyramids", confidence=0.90, source="gemini",
                       description="The last surviving wonder of the ancient world")
    merged = merge_landmark(onnx=onnx, gemini=gemini, grok=None, onnx_top3=[])
    log_result(
        "Agreement boost",
        merged.slug == "pyramids_of_giza" and merged.confidence >= 0.85,
        f"slug={merged.slug}, conf={merged.confidence:.2f}, agree={merged.agreement}",
    )

    # Gemini-only (ONNX failed)
    merged2 = merge_landmark(onnx=None, gemini=gemini, grok=None, onnx_top3=[])
    log_result("Gemini-only fallback", merged2.slug == "pyramids_of_giza", f"source={merged2.source}")

    # Neither (both failed)
    merged3 = merge_landmark(onnx=None, gemini=None, grok=None, onnx_top3=[])
    log_result("Both failed → empty slug", merged3.slug == "", f"slug='{merged3.slug}'")


def test_cloudflare_service():
    """Test 3: CloudflareService structure and methods."""
    print("\n── Test 3: CloudflareService Structure ──")
    from app.core.cloudflare_service import CloudflareService

    svc = CloudflareService(api_token="test", account_id="test_acct")
    log_result("CloudflareService.available", svc.available is True)
    log_result("has identify_landmark", hasattr(svc, "identify_landmark"))
    log_result("has vision_json", hasattr(svc, "vision_json"))
    log_result("has close", hasattr(svc, "close"))
    expected_url = "https://api.cloudflare.com/client/v4/accounts/test_acct/ai/run/@cf/meta/llama-3.2-11b-vision-instruct"
    log_result("URL construction", svc._url(svc.vision_model) == expected_url)

    svc2 = CloudflareService(api_token="", account_id="test")
    log_result("unavailable when no token", svc2.available is False)


def test_tla_service():
    """Test 4: TLAService structure and methods."""
    print("\n── Test 4: TLAService Structure ──")
    from app.core.tla_service import TLAService

    svc = TLAService()
    log_result("TLAService.available", svc.available is True)
    log_result("has search_lemma", hasattr(svc, "search_lemma"))
    log_result("has get_lemma", hasattr(svc, "get_lemma"))
    log_result("has close", hasattr(svc, "close"))


def test_fallback_wiring():
    """Test 7: Verify fallback chain is properly wired in explore.py."""
    print("\n── Test 7: Fallback Chain Wiring ──")
    import inspect
    from app.api.explore import identify_landmark

    src = inspect.getsource(identify_landmark)
    checks = [
        ("ONNX + Gemini parallel", "_run_onnx" in src and "_run_gemini_vision" in src),
        ("Groq fallback (Step 1b)", "_run_groq_vision" in src and "Step 1b" in src),
        ("Cloudflare fallback (Step 1c)", "_run_cloudflare_vision" in src and "Step 1c" in src),
        ("Grok tiebreaker (Step 2)", "_run_grok_vision" in src and "tiebreak" in src.lower()),
        ("Merge step (Step 3)", "merge_landmark" in src),
        ("Not-Egyptian detection", "is_egyptian" in src),
    ]
    for name, result in checks:
        log_result(name, result)


async def test_live_endpoint():
    """Test 5+6: Live endpoint tests (requires running server)."""
    print("\n── Test 5-6: Live Endpoint (requires server at :8000) ──")
    try:
        import httpx
    except ImportError:
        log_result("httpx import", False, "pip install httpx")
        return

    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=30.0) as client:
        try:
            resp = await client.get("/api/health")
            if resp.status_code != 200:
                print("  [SKIP] Server not running at localhost:8000")
                return
        except httpx.ConnectError:
            print("  [SKIP] Server not running at localhost:8000")
            return

        # Test 5: Happy path with a real landmark image if available
        import cv2
        import numpy as np

        test_img = ROOT / "data" / "landmark_classification" / "test" / "abu_simbel"
        if test_img.exists():
            images = list(test_img.glob("*.png")) + list(test_img.glob("*.jpg"))
            if images:
                image_bytes = images[0].read_bytes()
                resp = await client.post(
                    "/api/explore/identify",
                    files={"file": (images[0].name, image_bytes, "image/jpeg")},
                )
                log_result(
                    "Known landmark returns 200/503",
                    resp.status_code in (200, 503),
                    f"status={resp.status_code}",
                )
                if resp.status_code == 200:
                    data = resp.json()
                    log_result(
                        "Response has required fields",
                        all(k in data for k in ("name", "slug", "confidence", "is_egyptian")),
                        f"keys={list(data.keys())}",
                    )
            else:
                print("  [SKIP] No test images in abu_simbel dir")
        else:
            # Fallback: generate synthetic image
            img = np.zeros((300, 300, 3), dtype=np.uint8)
            pts = np.array([[150, 50], [50, 250], [250, 250]], np.int32)
            cv2.fillPoly(img, [pts], (200, 190, 150))
            _, buf = cv2.imencode(".jpg", img)
            resp = await client.post(
                "/api/explore/identify",
                files={"file": ("test.jpg", bytes(buf), "image/jpeg")},
            )
            log_result("Synthetic image returns 200/503", resp.status_code in (200, 503), f"status={resp.status_code}")

        # Test 6: Not-Egyptian (solid blue)
        blue = np.full((300, 300, 3), (255, 100, 50), dtype=np.uint8)
        _, blue_buf = cv2.imencode(".jpg", blue)
        resp2 = await client.post(
            "/api/explore/identify",
            files={"file": ("blue.jpg", bytes(blue_buf), "image/jpeg")},
        )
        log_result("Not-Egyptian returns 200/503", resp2.status_code in (200, 503), f"status={resp2.status_code}")


def main():
    print("=" * 60)
    print("Wadjet v2 — Identify Pipeline Test Suite")
    print("=" * 60)

    test_service_imports()
    test_ensemble_merge()
    test_cloudflare_service()
    test_tla_service()
    test_fallback_wiring()
    asyncio.run(test_live_endpoint())

    print("\n" + "=" * 60)
    print(f"Results: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print("=" * 60)
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
