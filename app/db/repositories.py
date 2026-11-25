from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import LoginEvent, UserProfile


class LoginEventRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, event: LoginEvent) -> LoginEvent:
        self.session.add(event)
        self.session.flush()
        return event

    def get_by_id(self, event_id: int) -> LoginEvent | None:
        return self.session.get(LoginEvent, event_id)

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


class UserProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_user_id(self, user_id: str) -> UserProfile | None:
        return self.session.get(UserProfile, user_id)

    def save(self, profile: UserProfile) -> UserProfile:
        saved_profile = self.session.merge(profile)
        self.session.flush()
        return saved_profile
