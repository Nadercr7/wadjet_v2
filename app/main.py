import logging
import re
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api import audio, auth, chat, dictionary, explore, feedback, health, pages, quiz, scan, stories, translate, user, write
from app.config import settings
from app.rate_limit import limiter

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, clean up on shutdown."""
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
    from app.db.database import init_db
    await init_db()
    logger.info("Database initialized")

    yield  # app runs here

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
            # GET-only endpoint — no state mutation
            re.compile(r"^/api/health$"),
            # Auth bootstrap — no session/cookie exists yet to carry CSRF token
            re.compile(r"^/api/auth/login$"),
            re.compile(r"^/api/auth/register$"),
            re.compile(r"^/api/auth/refresh$"),
            # Logout — destroys session, safe to exempt
            re.compile(r"^/api/auth/logout$"),
            # OAuth + email flows — no CSRF cookie on first request
            re.compile(r"^/api/auth/google$"),
            re.compile(r"^/api/auth/verify-email$"),
            re.compile(r"^/api/auth/forgot-password$"),
            re.compile(r"^/api/auth/reset-password$"),
            re.compile(r"^/api/auth/send-verification$"),
            # AJAX-only API endpoints — protected by CORS same-origin, no cookie mutation
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
            # Read-only documentation (disabled in production via Phase 2)
            re.compile(r"^/docs"),
            re.compile(r"^/openapi\.json$"),
        ],
    )

    # Global 500 handler — never leak internals to clients
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
        return JSONResponse(status_code=500, content={"detail": "An internal error occurred. Please try again later."})

    # GZip compression for responses > 500 bytes
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Security response headers
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(self), microphone=(self), geolocation=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://accounts.google.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://accounts.google.com; "
            "img-src 'self' data: blob: https:; "
            "media-src 'self' blob:; "
            "connect-src 'self' blob: https://accounts.google.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "frame-src https://accounts.google.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        # Persist ?lang= query param as cookie for hreflang / crawler support
        lang_param = request.query_params.get("lang")
        if lang_param in ("en", "ar"):
            secure = "; Secure" if request.url.scheme == "https" else ""
            response.set_cookie(
                key="wadjet_lang",
                value=lang_param,
                path="/",
                max_age=31536000,
                samesite="lax",
                secure=request.url.scheme == "https",
            )
        return response

    # Static files
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

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

    # Routes
    app.include_router(pages.router)
    app.include_router(scan.router)
    app.include_router(translate.router)
    app.include_router(dictionary.router)
    app.include_router(write.router)
    app.include_router(explore.router)
    app.include_router(explore.identify_router)
    app.include_router(chat.router)
    app.include_router(quiz.router)
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
