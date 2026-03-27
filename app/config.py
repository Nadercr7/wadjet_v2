from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000

    # Gemini
    gemini_api_keys: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_lite_model: str = "gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-001"

    # Model paths
    hieroglyph_detector_path: str = "models/hieroglyph/detector/glyph_detector_uint8.onnx"
    hieroglyph_classifier_path: str = (
        "models/hieroglyph/classifier/hieroglyph_classifier_uint8.onnx"
    )
    label_mapping_path: str = "models/hieroglyph/label_mapping.json"
    landmark_model_path: str = "models/landmark/landmark_classifier_uint8.onnx"
    landmark_label_mapping_path: str = "models/landmark/landmark_label_mapping.json"
    faiss_index_path: str = "data/embeddings/corpus.index"
    corpus_path: str = "data/embeddings/corpus_ids.json"

    # Detection tuning
    detection_confidence_threshold: float = 0.15

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.parent

    @property
    def gemini_keys_list(self) -> list[str]:
        return [k.strip() for k in self.gemini_api_keys.split(",") if k.strip()]


settings = Settings()
