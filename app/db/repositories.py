from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LoginEvent, LoginFeedback, UserProfile


class LoginEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, event: LoginEvent) -> LoginEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def get_by_id(self, event_id: int) -> LoginEvent | None:
        return self.session.get(LoginEvent, event_id)

    def get_by_event_id(self, event_id: str) -> LoginEvent | None:
        statement = select(LoginEvent).where(LoginEvent.event_id == event_id)
        return self.session.scalar(statement)

    def list_for_user(
        self,
        user_id: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[LoginEvent]:
        if limit < 1:
            raise ValueError("limit must be greater than zero")
        if offset < 0:
            raise ValueError("offset cannot be negative")

        statement = (
            select(LoginEvent)
            .where(LoginEvent.user_id == user_id)
            .order_by(LoginEvent.timestamp.desc(), LoginEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(statement))

    def list_for_user_before(
        self,
        user_id: str,
        before: datetime,
        *,
        limit: int = 100,
    ) -> list[LoginEvent]:
        if limit < 1:
            raise ValueError("limit must be greater than zero")
        if before.utcoffset() is None:
            raise ValueError("before must be timezone-aware")

        statement = (
            select(LoginEvent)
            .where(LoginEvent.user_id == user_id, LoginEvent.timestamp < before)
            .order_by(LoginEvent.timestamp.desc(), LoginEvent.id.desc())
            .limit(limit)
        )
        return list(self.session.scalars(statement))

    def distinct_users_for_ip_between(
        self,
        ip: str,
        since: datetime,
        before: datetime,
    ) -> set[str]:
        if since.utcoffset() is None or before.utcoffset() is None:
            raise ValueError("time bounds must be timezone-aware")
        if since >= before:
            raise ValueError("since must be before before")

        statement = (
            select(LoginEvent.user_id)
            .where(
                LoginEvent.ip == ip,
                LoginEvent.timestamp >= since,
                LoginEvent.timestamp < before,
            )
            .distinct()
        )
        return set(self.session.scalars(statement))


class UserProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_user_id(self, user_id: str) -> UserProfile | None:
        return self.session.get(UserProfile, user_id)

    def save(self, profile: UserProfile) -> UserProfile:
        saved_profile = self.session.merge(profile)
        self.session.flush()
        return saved_profile


class LoginFeedbackRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_for_login_event(self, login_event_id: int) -> LoginFeedback | None:
        statement = select(LoginFeedback).where(
            LoginFeedback.login_event_id == login_event_id
        )
        return self.session.scalar(statement)

    def add(self, feedback: LoginFeedback) -> LoginFeedback:
        self.session.add(feedback)
        self.session.flush()
        return feedback
