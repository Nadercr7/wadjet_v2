import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import chat, dictionary, explore, health, pages, quiz, scan, write
from app.config import settings

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

    yield  # app runs here

    # Cleanup
    app.state.gemini = None


def create_app() -> FastAPI:
    app = FastAPI(
        title="Wadjet",
        description="AI-powered Egyptian heritage app",
        version="2.0.0",
        lifespan=lifespan,
    )

    # GZip compression for responses > 500 bytes
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # Static files
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

    # Serve ML models for client-side pipeline (ONNX + TF.js)
    models_dir = BASE_DIR.parent / "models"
    if models_dir.exists():
        app.mount("/models", StaticFiles(directory=models_dir), name="models")

    # Templates
    templates = Jinja2Templates(directory=BASE_DIR / "templates")
    app.state.templates = templates

    # Routes
    app.include_router(pages.router)
    app.include_router(scan.router)
    app.include_router(dictionary.router)
    app.include_router(write.router)
    app.include_router(explore.router)
    app.include_router(explore.identify_router)
    app.include_router(chat.router)
    app.include_router(quiz.router)
    app.include_router(health.router, prefix="/api")

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
