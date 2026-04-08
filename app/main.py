import logging
import re
import secrets
from contextlib import asynccontextmanager
from datetime import UTC
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import (
    audio,
    auth,
    chat,
    dictionary,
    explore,
    feedback,
    health,
    pages,
    scan,
    stories,
    translate,
    user,
    write,
)
from app.config import settings
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


def _setup_persistent_storage():
    """Set up symlinks from ephemeral paths to persistent volume.

    HF Spaces mounts persistent storage at PERSISTENT_DATA_DIR (e.g. /data).
    We symlink app/static/cache → /data/cache so generated TTS audio and
    AI images persist across container rebuilds. The SQLite DB URL is already
    rewritten by config.py to point inside the persistent dir.
    """
    pdir = settings.persistent_data_dir
    if not pdir:
        return

    pdir = Path(pdir)
    if not pdir.exists():
        logger.warning("PERSISTENT_DATA_DIR=%s does not exist — skipping", pdir)
        return

    logger.info("Persistent storage: %s", pdir)

    # Ensure subdirectories exist on persistent volume
    (pdir / "cache" / "audio").mkdir(parents=True, exist_ok=True)
    (pdir / "cache" / "images").mkdir(parents=True, exist_ok=True)

    # Symlink app/static/cache → persistent/cache
    cache_link = BASE_DIR / "static" / "cache"
    persistent_cache = pdir / "cache"

    if cache_link.is_symlink():
        # Already linked (e.g. from a previous startup without rebuild)
        logger.info("Cache symlink already exists: %s → %s", cache_link, cache_link.resolve())
    elif cache_link.is_dir():
        # Copy pre-generated story images to persistent storage before destroying
        import shutil
        src_images = cache_link / "images"
        dst_images = persistent_cache / "images"
        if src_images.is_dir():
            for f in src_images.glob("story_*.png"):
                dst = dst_images / f.name
                if not dst.exists():
                    shutil.copy2(f, dst)
                    logger.info("Copied pre-generated image to persistent: %s", f.name)
        shutil.rmtree(cache_link)
        cache_link.symlink_to(persistent_cache)
        logger.info("Replaced cache dir with symlink: %s → %s", cache_link, persistent_cache)
    else:
        cache_link.symlink_to(persistent_cache)
        logger.info("Created cache symlink: %s → %s", cache_link, persistent_cache)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, clean up on shutdown."""
    # ── Persistent storage setup (HF Spaces) ──
    # When PERSISTENT_DATA_DIR is set, use it for DB + cache so data
    # survives container rebuilds on push.
    _setup_persistent_storage()

    # Initialize Gemini
    keys = settings.gemini_keys_list
    if keys:
        from app.core.gemini_service import GeminiService
        app.state.gemini = GeminiService(keys, default_model=settings.gemini_model)
        logger.info("GeminiService ready with %d keys", len(keys))
    else:
        app.state.gemini = None
        logger.warning("No Gemini API keys — AI features disabled")

    # Initialize Grok
    grok_keys = settings.grok_keys_list
    if grok_keys:
        from app.core.grok_service import GrokService
        app.state.grok = GrokService(grok_keys, default_model=settings.grok_model)
        logger.info("GrokService ready with %d keys", len(grok_keys))
    else:
        app.state.grok = None
        logger.info("No Grok API keys — tiebreaker disabled")

    # Initialize Groq
    groq_keys = settings.groq_keys_list
    if groq_keys:
        from app.core.groq_service import GroqService
        app.state.groq = GroqService(
            groq_keys,
            vision_model=settings.groq_vision_model,
            text_model=settings.groq_text_model,
        )
        logger.info("GroqService ready with %d keys", len(groq_keys))
    else:
        app.state.groq = None
        logger.info("No Groq API key — Groq fallback disabled")

    # Initialize Cloudflare Workers AI
    if settings.cloudflare_api_token and settings.cloudflare_account_id:
        from app.core.cloudflare_service import CloudflareService
        app.state.cloudflare = CloudflareService(
            api_token=settings.cloudflare_api_token,
            account_id=settings.cloudflare_account_id,
            vision_model=settings.cloudflare_vision_model,
        )
        logger.info("CloudflareService ready")
    else:
        app.state.cloudflare = None
        logger.info("No Cloudflare credentials — Cloudflare fallback disabled")

    # Initialize unified AIService (wraps Gemini + Groq + Grok)
    from app.core.ai_service import AIService
    app.state.ai_service = AIService(
        gemini=app.state.gemini,
        groq=app.state.groq,
        grok=app.state.grok,
    )

    # Initialize AI Hieroglyph Reader
    from app.core.ai_reader import AIHieroglyphReader
    app.state.ai_reader = AIHieroglyphReader(app.state.ai_service)

    # Initialize RAG Translator (Gemini embeddings + fallback chain)
    from app.core.rag_translator import RAGTranslator
    app.state.translator = RAGTranslator(
        gemini=app.state.gemini,
        ai_service=app.state.ai_service,
    )
    logger.info(
        "RAGTranslator ready (index=%s)",
        "loaded" if app.state.translator.available else "unavailable",
    )

    # Initialize TLA (Thesaurus Linguae Aegyptiae) — free, no auth
    from app.core.tla_service import TLAService
    app.state.tla = TLAService()
    logger.info("TLAService ready")

    # Initialize database
    # SQLite: always create_all() (ephemeral on HF Spaces, no migration state)
    # PostgreSQL: skip create_all(), rely on Alembic migrations
    if "sqlite" in settings.database_url:
        from app.db.database import init_db
        await init_db()
        logger.info("SQLite database initialized (create_all)")

        # Patch persistent DB schema if columns are missing (create_all doesn't
        # add columns to existing tables — only creates missing tables).
        # Also check for SQLite corruption (common on HF Spaces after crashes).
        try:
            from sqlalchemy import text as sa_text
            from app.db.database import engine as db_engine

            async with db_engine.begin() as conn:
                # Quick integrity check
                result = await conn.execute(sa_text("PRAGMA integrity_check"))
                integrity = result.scalar()
                if integrity != "ok":
                    logger.error("SQLite INTEGRITY CHECK FAILED: %s", integrity)

                _REQUIRED_USER_COLS = {
                    "google_id": "VARCHAR",
                    "auth_provider": "VARCHAR DEFAULT 'email'",
                    "email_verified": "BOOLEAN DEFAULT 0",
                    "avatar_url": "VARCHAR",
                }
                rows = await conn.execute(sa_text("PRAGMA table_info(users)"))
                existing = {r[1] for r in rows}
                for col, col_type in _REQUIRED_USER_COLS.items():
                    if col not in existing:
                        await conn.execute(sa_text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
                        logger.warning("Auto-added missing column users.%s", col)
        except Exception as e:
            logger.error("Schema patch failed: %s", e)
    else:
        logger.info("PostgreSQL database ready (use 'alembic upgrade head' for migrations)")

    # Pre-warm ONNX models + inject app-level translator into pipeline
    try:
        import asyncio

        from app.core.landmark_pipeline import LandmarkPipeline
        from app.dependencies import get_pipeline

        pipeline = get_pipeline()
        # Inject app-level translator so pipeline has full AI access (HIERO-006)
        if app.state.translator:
            pipeline.set_translator(app.state.translator)

        # Pre-warm ONNX sessions in thread pool (avoids first-request penalty)
        await asyncio.to_thread(pipeline._get_detector)
        await asyncio.to_thread(pipeline._get_classifier)
        logger.info("Hieroglyph ONNX models pre-warmed")

        # Pre-warm landmark model
        landmark_pipeline = LandmarkPipeline()
        await asyncio.to_thread(landmark_pipeline._get_session)
        app.state.landmark_pipeline = landmark_pipeline
        logger.info("Landmark ONNX model pre-warmed")
    except Exception as e:
        logger.warning("Model pre-warm failed (will lazy-load on first request): %s", e)

    # Clean up expired tokens on startup
    try:
        from datetime import datetime

        from sqlalchemy import delete as sa_delete

        from app.db.database import async_session
        from app.db.models import EmailToken, RefreshToken
        async with async_session() as db:
            now = datetime.now(UTC)
            result_rt = await db.execute(
                sa_delete(RefreshToken).where(RefreshToken.expires_at < now)
            )
            result_et = await db.execute(
                sa_delete(EmailToken).where(EmailToken.expires_at < now)
            )
            await db.commit()
            total = result_rt.rowcount + result_et.rowcount
            if total > 0:
                logger.info("Cleaned up %d expired tokens on startup", total)
    except Exception as e:
        logger.warning("Token cleanup skipped: %s", e)

    yield  # app runs here

    # Flush enrichment cache before shutdown
    try:
        from app.api.explore import enrichment_cache
        if enrichment_cache._dirty:
            await enrichment_cache.save_async()
    except Exception:
        pass

    # Cleanup
    if hasattr(app.state, "ai_service") and app.state.ai_service:
        await app.state.ai_service.close()
    if app.state.grok:
        await app.state.grok.close()
    if hasattr(app.state, "cloudflare") and app.state.cloudflare:
        await app.state.cloudflare.close()
    app.state.cloudflare = None
    app.state.grok = None
    app.state.groq = None
    app.state.gemini = None
    app.state.ai_service = None
    app.state.ai_reader = None
    app.state.translator = None
    if hasattr(app.state, "tla") and app.state.tla:
        await app.state.tla.close()
    app.state.tla = None
    # Close shared image generation HTTP client
    from app.core.image_service import close_image_client
    await close_image_client()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Wadjet",
        description="AI-powered Egyptian heritage app",
        version="3.0.0-beta",
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    # ── Security middleware ──

    # Rate limiter
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CSRF protection for POST/PUT/DELETE (skip GET, health, docs, auth)
    if not settings.csrf_secret:
        settings.csrf_secret = secrets.token_hex(32)
    csrf_secret = settings.csrf_secret
    # Ensure JWT secret is set (auto-generate for dev, must be env var in production)
    if not settings.jwt_secret:
        settings.jwt_secret = secrets.token_hex(32)
    from starlette_csrf import CSRFMiddleware
    app.add_middleware(
        CSRFMiddleware,
        secret=csrf_secret,
        exempt_urls=[
            # ── GET-only (no state mutation) ──
            re.compile(r"^/api/health$"),
            # ── Stateless auth bootstrap (no session cookie exists yet) ──
            re.compile(r"^/api/auth/login$"),
            re.compile(r"^/api/auth/register$"),
            re.compile(r"^/api/auth/refresh$"),
            re.compile(r"^/api/auth/logout$"),
            re.compile(r"^/api/auth/google$"),
            re.compile(r"^/api/auth/verify-email$"),
            re.compile(r"^/api/auth/forgot-password$"),
            re.compile(r"^/api/auth/reset-password$"),
            re.compile(r"^/api/auth/send-verification$"),
            # ── Bearer-token-authenticated AJAX endpoints ──
            # These are CSRF-immune: browser doesn't auto-attach Authorization headers.
            # All require `Authorization: Bearer <jwt>` from JS fetch(), not cookies.
            re.compile(r"^/api/audio/"),
            re.compile(r"^/api/scan$"),
            re.compile(r"^/api/translate$"),
            re.compile(r"^/api/write"),
            re.compile(r"^/api/chat"),
            re.compile(r"^/api/landmarks"),
            re.compile(r"^/api/explore"),
            re.compile(r"^/api/dictionary"),
            re.compile(r"^/api/stories"),
            re.compile(r"^/api/user"),
            re.compile(r"^/api/feedback$"),
            # ── Dev-only docs (disabled in production) ──
            re.compile(r"^/docs"),
            re.compile(r"^/openapi\.json$"),
        ],
    )

    # ── Branded error pages (404 / 500) ──
    def _error_context(request: Request, code: int, title: str, message: str) -> dict:
        lang = request.cookies.get("wadjet_lang", "en")
        return {
            "request": request, "lang": lang,
            "error_code": code, "error_title": title, "error_message": message,
            "page_name": "error",
        }

    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc):
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        tpl = app.state.templates
        ctx = _error_context(request, 404, "Page Not Found",
                             "The ancient scrolls contain no record of this path.")
        return HTMLResponse(tpl.get_template("error.html").render(**ctx), status_code=404)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=500, content={"detail": "An internal error occurred. Please try again later."})
        try:
            tpl = app.state.templates
            ctx = _error_context(request, 500, "Something Went Wrong",
                                 "The temple scribes are investigating. Please try again shortly.")
            return HTMLResponse(tpl.get_template("error.html").render(**ctx), status_code=500)
        except Exception:
            return JSONResponse(status_code=500, content={"detail": "An internal error occurred. Please try again later."})

    # GZip compression for responses > 500 bytes
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Security response headers
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://accounts.google.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com; "
            "img-src 'self' data: blob: https:; "
            "media-src 'self' blob:; "
            "connect-src 'self' blob: https://accounts.google.com https://oauth2.googleapis.com https://www.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "frame-src https://accounts.google.com; "
            "frame-ancestors 'self' https://huggingface.co https://*.hf.space; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        # HSTS — only in production (HTTPS guaranteed)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # Persist ?lang= query param as cookie for hreflang / crawler support
        lang_param = request.query_params.get("lang")
        if lang_param in ("en", "ar"):
            response.set_cookie(
                key="wadjet_lang",
                value=lang_param,
                path="/",
                max_age=31536000,
                samesite="lax",
                secure=request.url.scheme == "https",
            )
        return response

    # Cache headers for static assets (1 year, immutable — cache-busted via ?v=N)
    @app.middleware("http")
    async def static_cache_headers(request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/") or request.url.path.startswith("/models/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response

    # Static files (follow_symlink=True for cache → persistent storage symlink)
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static", follow_symlink=True), name="static")

    # Serve ML models for client-side pipeline (ONNX + TF.js)
    models_dir = BASE_DIR.parent / "models"
    if models_dir.exists():
        app.mount("/models", StaticFiles(directory=models_dir), name="models")

    # Templates
    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    app.state.templates = templates

    # i18n — register t() as Jinja2 global for all templates
    from app.i18n import t as _translate
    templates.env.globals["t"] = _translate
    templates.env.globals["base_url"] = settings.base_url.rstrip("/")
    templates.env.globals["google_client_id"] = settings.google_client_id
    templates.env.globals["admin_email"] = settings.admin_email

    # Routes
    app.include_router(pages.router)
    app.include_router(scan.router)
    app.include_router(translate.router)
    app.include_router(dictionary.router)
    app.include_router(write.router)
    app.include_router(explore.router)
    app.include_router(explore.identify_router)
    app.include_router(chat.router)
    app.include_router(stories.router)
    app.include_router(auth.router)
    app.include_router(user.router)
    app.include_router(audio.router)
    app.include_router(health.router, prefix="/api")
    app.include_router(feedback.router)

    # Service Worker — must be served from root for scope='/'
    sw_path = BASE_DIR / "static" / "sw.js"

    @app.get("/sw.js", include_in_schema=False)
    async def service_worker():
        return FileResponse(sw_path, media_type="application/javascript")

    # Favicon
    favicon_path = BASE_DIR / "static" / "images" / "favicon.svg"

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(favicon_path, media_type="image/svg+xml")

    return app


app = create_app()
