from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, IPvAnyAddress

Decision = Literal["allow", "challenge", "deny"]


class LoginEventRequest(BaseModel):
    user_id: str = Field(min_length=1)
    ip: IPvAnyAddress
    user_agent: str = Field(min_length=1)
    device_id: str = Field(min_length=1)
    timestamp: datetime
    success: bool


class LoginEventResponse(BaseModel):
    event_id: str
    risk_score: int = Field(ge=0, le=100)
    decision: Decision
    reasons: list[str]
