from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, IPvAnyAddress, field_validator

Decision = Literal["allow", "challenge", "deny"]
FeedbackLabel = Literal["real_attack", "false_positive"]


class LoginEventRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "user_id": "user_123",
                    "ip": "203.0.113.42",
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "device_id": "device_7",
                    "timestamp": "2026-03-01T10:15:00Z",
                    "success": True,
                }
            ]
        }
    )

    user_id: str = Field(min_length=1)
    ip: IPvAnyAddress
    user_agent: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    timestamp: datetime
    success: bool

    @field_validator("timestamp")
    @classmethod
    def require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    @field_validator("user_agent")
    @classmethod
    def require_non_blank_user_agent(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("user_agent cannot be empty")
        return value


class LoginEventResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "event_id": "evt_0123456789abcdef0123456789abcdef",
                    "risk_score": 0,
                    "decision": "allow",
                    "reasons": [],
                }
            ]
        }
    )

    event_id: str
    risk_score: int = Field(ge=0, le=100)
    decision: Decision
    reasons: list[str]


class FeedbackRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "event_id": "evt_0123456789abcdef0123456789abcdef",
                    "label": "real_attack",
                }
            ]
        }
    )

    event_id: str = Field(pattern=r"^evt_[0-9a-f]{32}$")
    label: FeedbackLabel


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "event_id": "evt_0123456789abcdef0123456789abcdef",
                    "label": "real_attack",
                }
            ]
        }
    )

    event_id: str
    label: FeedbackLabel


class RiskHistoryEntry(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "event_id": "evt_0123456789abcdef0123456789abcdef",
                    "timestamp": "2026-03-01T10:15:00Z",
                    "risk_score": 0,
                    "decision": "allow",
                    "reasons": [],
                }
            ]
        }
    )

    event_id: str | None
    timestamp: datetime
    risk_score: int | None = Field(default=None, ge=0, le=100)
    decision: Decision | None = None
    reasons: list[str]

    @field_validator("timestamp")
    @classmethod
    def require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("timestamp must be timezone-aware")
        return value


class RiskHistoryResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "events": [
                        {
                            "event_id": "evt_0123456789abcdef0123456789abcdef",
                            "timestamp": "2026-03-01T10:15:00Z",
                            "risk_score": 0,
                            "decision": "allow",
                            "reasons": [],
                        }
                    ],
                    "limit": 20,
                    "offset": 0,
                }
            ]
        }
    )

    events: list[RiskHistoryEntry]
    limit: int
    offset: int


class HealthResponse(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "ok"}]})

    status: Literal["ok"]
