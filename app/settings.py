from functools import lru_cache
from ipaddress import ip_network
from pathlib import Path
from typing import Self

from pydantic import Field, SecretStr, field_validator, model_validator
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
    geoip_enabled: bool = False
    high_risk_ip_networks: list[str] = Field(default_factory=list)
    model_path: Path = Path("artifacts/model.joblib")
    ml_enabled: bool = False
    rate_limit_enabled: bool = False
    rate_limit_max_requests: int = Field(default=100, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)
    credential_stuffing_window_seconds: int = Field(default=300, ge=1)
    shadow_mode: bool = True
    allow_max_score: int = 39
    challenge_max_score: int = 78

    @field_validator("high_risk_ip_networks")
    @classmethod
    def validate_high_risk_ip_networks(cls, networks: list[str]) -> list[str]:
        for network in networks:
            ip_network(network, strict=False)
        return networks

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
