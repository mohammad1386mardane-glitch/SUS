from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./sus.db"
    redis_url: str = "redis://localhost:6379/0"
    api_key: SecretStr = SecretStr("")
    geoip_db_path: Path = Path("data/GeoLite2-City.mmdb")
    model_path: Path = Path("artifacts/model.joblib")
    shadow_mode: bool = True
