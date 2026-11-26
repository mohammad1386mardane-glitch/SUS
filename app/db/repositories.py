from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
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

    def failed_user_device_pairs_for_ip_between(
        self,
        ip: str,
        since: datetime,
        before: datetime,
    ) -> set[tuple[str, str]]:
        if since.utcoffset() is None or before.utcoffset() is None:
            raise ValueError("time bounds must be timezone-aware")
        if since >= before:
            raise ValueError("since must be before before")

        statement = (
            select(LoginEvent.user_id, LoginEvent.device_id)
            .where(
                LoginEvent.ip == ip,
                LoginEvent.timestamp >= since,
                LoginEvent.timestamp < before,
                LoginEvent.success.is_(False),
            )
            .distinct()
        )
        return {
            (user_id, device_id)
            for user_id, device_id in self.session.execute(statement)
        }


class UserProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_user_id(self, user_id: str) -> UserProfile | None:
        return self.session.get(UserProfile, user_id)

    def save(self, profile: UserProfile) -> UserProfile:
        saved_profile = self.session.merge(profile)
        self.session.flush()
        return saved_profile

    def add_trusted_login(
        self,
        *,
        user_id: str,
        device_id: str,
        country: str | None,
        hour: int,
    ) -> UserProfile:
        statement = (
            select(UserProfile)
            .where(UserProfile.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        profile = self.session.scalar(statement)
        if profile is None:
            dialect_name = self.session.get_bind().dialect.name
            if dialect_name == "postgresql":
                self.session.execute(
                    postgresql_insert(UserProfile)
                    .values(
                        user_id=user_id,
                        usual_countries=[],
                        usual_devices=[],
                        usual_hours=[],
                    )
                    .on_conflict_do_nothing(index_elements=[UserProfile.user_id])
                )
            elif dialect_name == "sqlite":
                self.session.execute(
                    sqlite_insert(UserProfile)
                    .values(
                        user_id=user_id,
                        usual_countries=[],
                        usual_devices=[],
                        usual_hours=[],
                    )
                    .on_conflict_do_nothing(index_elements=[UserProfile.user_id])
                )
            else:
                raise NotImplementedError(
                    f"Trusted profile learning is unsupported for {dialect_name}"
                )
            profile = self.session.scalar(statement)
            if profile is None:
                raise RuntimeError("Unable to create or load user profile")

        if device_id not in profile.usual_devices:
            profile.usual_devices = [*profile.usual_devices, device_id]

        normalized_country = country.strip().upper() if country else None
        known_countries = {item.strip().upper() for item in profile.usual_countries}
        if normalized_country and normalized_country not in known_countries:
            profile.usual_countries = [*profile.usual_countries, normalized_country]

        if hour not in profile.usual_hours:
            profile.usual_hours = [*profile.usual_hours, hour]

        self.session.flush()
        return profile


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
