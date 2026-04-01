import logging
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings

_log = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 7860

    # Security
    csrf_secret: str = ""  # Auto-generated if empty (see main.py)
    jwt_secret: str = ""  # Auto-generated if empty (see main.py)
    trusted_proxy_depth: int = 1  # 0=direct, 1=one reverse proxy (Render)
    base_url: str = "https://nadercr7-wadjet-v2.hf.space"  # Override in .env for custom domain

    # Admin
    admin_email: str = "naderelakany@gmail.com"

    # Database
    # HF Spaces persistent storage: when PERSISTENT_DATA_DIR is set (e.g. /data),
    # the DB + cache survive container rebuilds across pushes.
    persistent_data_dir: str = ""  # Set via HF Space env var (e.g. /data)
    database_url: str = "sqlite+aiosqlite:///data/wadjet.db"

    # Gemini
    gemini_api_keys: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_lite_model: str = "gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"

    # Grok (xAI)
    grok_api_keys: str = ""
    grok_model: str = "grok-4-latest"

    # Groq
    groq_api_keys: str = ""
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_text_model: str = "llama-3.3-70b-versatile"

    # Cloudflare Workers AI
    cloudflare_api_token: str = ""
    cloudflare_account_id: str = ""
    cloudflare_vision_model: str = "@cf/meta/llama-3.2-11b-vision-instruct"

    # Google Sign-In
    google_client_id: str = ""
    google_client_secret: str = ""

    # Email (Resend)
    resend_api_key: str = ""

    # HuggingFace deployment
    hf_token: str = ""

    # Model paths
    hieroglyph_detector_path: str = "models/hieroglyph/detector/glyph_detector_uint8.onnx"
    hieroglyph_classifier_path: str = (
        "models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx"
    )
    label_mapping_path: str = "models/hieroglyph/classifier/label_mapping.json"
    landmark_model_path: str = "models/landmark/landmark_classifier_uint8.onnx"
    landmark_label_mapping_path: str = "models/landmark/landmark_label_mapping.json"
    faiss_index_path: str = "data/embeddings/corpus.index"
    corpus_path: str = "data/embeddings/corpus_ids.json"

    # Detection tuning
    detection_confidence_threshold: float = 0.15

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> "Settings":
        """Refuse to start in production without real secrets."""
        # When persistent storage is configured, redirect SQLite DB there
        if self.persistent_data_dir and "sqlite" in self.database_url:
            pdir = Path(self.persistent_data_dir)
            db_path = pdir / "wadjet.db"
            self.database_url = f"sqlite+aiosqlite:///{db_path}"
            _log.info("Using persistent database at %s", db_path)

        if self.environment != "development":
            if not self.jwt_secret:
                raise ValueError(
                    "JWT_SECRET is required when ENVIRONMENT != 'development'. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            if not self.csrf_secret:
                raise ValueError(
                    "CSRF_SECRET is required when ENVIRONMENT != 'development'. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
        # Warn about missing AI keys (non-fatal — features degrade gracefully)
        if self.environment != "development":
            if not self.gemini_api_keys.strip():
                _log.warning("GEMINI_API_KEYS not set — scan, translate, chat, TTS will be disabled")
            if not self.google_client_id:
                _log.warning("GOOGLE_CLIENT_ID not set — Google Sign-In will be disabled")
            if not self.resend_api_key:
                _log.warning("RESEND_API_KEY not set — email verification will be disabled")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def gemini_keys_list(self) -> list[str]:
        return [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]

    @property
    def grok_keys_list(self) -> list[str]:
        return [k.strip() for k in self.grok_api_keys.split(",") if k.strip()]

    @property
    def groq_keys_list(self) -> list[str]:
        return [k.strip() for k in self.groq_api_keys.split(",") if k.strip()]


settings = Settings()
