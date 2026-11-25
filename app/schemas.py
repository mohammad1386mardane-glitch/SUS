from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, IPvAnyAddress, field_validator

Decision = Literal["allow", "challenge", "deny"]
FeedbackLabel = Literal["real_attack", "false_positive"]


class LoginEventRequest(BaseModel):
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


class LoginEventResponse(BaseModel):
    event_id: str
    risk_score: int = Field(ge=0, le=100)
    decision: Decision
    reasons: list[str]


class FeedbackRequest(BaseModel):
    event_id: str = Field(pattern=r"^evt_[0-9a-f]{32}$")
    label: FeedbackLabel


class FeedbackResponse(BaseModel):
    event_id: str
    label: FeedbackLabel
