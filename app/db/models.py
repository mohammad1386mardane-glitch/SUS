from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LoginEvent(Base):
    __tablename__ = "login_events"
    __table_args__ = (
        CheckConstraint(
            "risk_score IS NULL OR risk_score BETWEEN 0 AND 100",
            name="ck_login_events_risk_score_range",
        ),
        CheckConstraint(
            "decision IS NULL OR decision IN ('allow', 'challenge', 'deny')",
            name="ck_login_events_decision",
        ),
        Index("ix_login_events_user_id_timestamp", "user_id", "timestamp"),
        Index("uq_login_events_event_id", "event_id", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str | None] = mapped_column(String(36))
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    ip: Mapped[str] = mapped_column(String(45), nullable=False)
    geo: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    device_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer)
    decision: Mapped[str | None] = mapped_column(String(16))
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LoginFeedback(Base):
    __tablename__ = "login_feedback"
    __table_args__ = (
        CheckConstraint(
            "label IN ('real_attack', 'false_positive')",
            name="ck_login_feedback_label",
        ),
        UniqueConstraint("login_event_id", name="uq_login_feedback_login_event_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login_event_id: Mapped[int] = mapped_column(
        ForeignKey("login_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    usual_countries: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )
    usual_devices: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    usual_hours: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
