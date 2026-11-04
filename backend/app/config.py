from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "Dancing with the SARs"
    API_V1_STR: str = "/api"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database (metadata only — rasters are never stored in SQLite)
    DATABASE_URL: str = f"sqlite:///{_PROJECT_ROOT / 'backend' / 'nisar.db'}"

    # Storage settings
    DATA_ROOT_DIR: str = str(_PROJECT_ROOT / "data")
    MAX_UPLOAD_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB default
    ALLOWED_EXTENSIONS: list[str] = [".tif", ".tiff", ".geojson", ".json"]

    # Guard against loading rasters that would exhaust memory in synchronous processing.
    MAX_RASTER_PIXELS: int = 60_000_000


settings = Settings()

# Domain identifiers accepted by dataset registration and processing endpoints.
VALID_DOMAINS = ["domain1", "domain2", "domain3", "domain4", "domain5", "unresolved"]
