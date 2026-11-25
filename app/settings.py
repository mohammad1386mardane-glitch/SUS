from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import SecretStr, model_validator
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
    allow_max_score: int = 39
    challenge_max_score: int = 78

    @model_validator(mode="after")
    def validate_score_thresholds(self) -> Self:
        if not 0 <= self.allow_max_score < self.challenge_max_score <= 100:
            raise ValueError(
                "score thresholds must satisfy "
                "0 <= allow_max_score < challenge_max_score <= 100"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
