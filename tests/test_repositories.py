from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import LoginEvent, UserProfile
from app.db.repositories import LoginEventRepository, UserProfileRepository


def create_event(
    user_id: str,
    timestamp: datetime,
    *,
    risk_score: int | None = 78,
    decision: str | None = "challenge",
) -> LoginEvent:
    return LoginEvent(
        user_id=user_id,
        ip="203.0.113.5",
        geo={"country": "US"},
        device_id="device-1",
        user_agent="test-agent",
        timestamp=timestamp,
        success=True,
        risk_score=risk_score,
        decision=decision,
        reasons=["new_device"],
    )


def test_login_event_repository_adds_and_pages_by_user(
    db_session: Session,
) -> None:
    repository = LoginEventRepository(db_session)
    first = create_event(
        "user-1",
        datetime(2026, 11, 25, 10, tzinfo=UTC),
    )
    second = create_event(
        "user-1",
        datetime(2026, 11, 25, 11, tzinfo=UTC),
    )
    other_user = create_event(
        "user-2",
        datetime(2026, 11, 25, 12, tzinfo=UTC),
    )

    repository.add(first)
    repository.add(second)
    repository.add(other_user)
    db_session.commit()

    assert repository.get_by_id(second.id) is second
    assert repository.get_by_id(-1) is None
    assert repository.list_for_user("user-1", limit=1) == [second]
    assert repository.list_for_user("user-1", limit=1, offset=1) == [first]
    assert repository.list_for_user("unknown") == []


def test_login_event_repository_filters_previous_events_and_distinct_ip_users(
    db_session: Session,
) -> None:
    repository = LoginEventRepository(db_session)
    window_start = datetime(2026, 11, 25, 11, 55, tzinfo=UTC)
    before = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
    events = (
        create_event("old-user", datetime(2026, 11, 25, 11, 54, tzinfo=UTC)),
        create_event("user-1", datetime(2026, 11, 25, 11, 56, tzinfo=UTC)),
        create_event("user-2", datetime(2026, 11, 25, 11, 57, tzinfo=UTC)),
        create_event("user-1", datetime(2026, 11, 25, 11, 58, tzinfo=UTC)),
        create_event("future-user", before),
    )
    for event in events:
        repository.add(event)
    db_session.commit()

    previous = repository.list_for_user_before("user-1", before, limit=1)
    users = repository.distinct_users_for_ip_between(
        "203.0.113.5",
        window_start,
        before,
    )

    assert [event.timestamp for event in previous] == [
        datetime(2026, 11, 25, 11, 58, tzinfo=UTC)
    ]
    assert users == {"user-1", "user-2"}


@pytest.mark.parametrize(
    ("limit", "offset"),
    [(0, 0), (1, -1)],
)
def test_login_event_repository_rejects_invalid_pagination(
    db_session: Session,
    limit: int,
    offset: int,
) -> None:
    repository = LoginEventRepository(db_session)

    with pytest.raises(ValueError):
        repository.list_for_user("user-1", limit=limit, offset=offset)


@pytest.mark.parametrize(
    ("risk_score", "decision"),
    [(101, "challenge"), (20, "unknown")],
)
def test_login_event_database_constraints_reject_invalid_values(
    db_session: Session,
    risk_score: int,
    decision: str,
) -> None:
    repository = LoginEventRepository(db_session)
    with pytest.raises(IntegrityError):
        repository.add(
            create_event(
                "user-1",
                datetime(2026, 11, 25, tzinfo=UTC),
                risk_score=risk_score,
                decision=decision,
            )
        )

    db_session.rollback()


def test_user_profile_repository_creates_and_updates_profile(
    db_session: Session,
) -> None:
    repository = UserProfileRepository(db_session)

    assert repository.get_by_user_id("user-1") is None
    profile = repository.save(UserProfile(user_id="user-1"))
    db_session.commit()
    assert profile.usual_countries == []
    assert profile.usual_devices == []
    assert profile.usual_hours == []
    assert profile.updated_at is not None

    updated = repository.save(
        UserProfile(
            user_id="user-1",
            usual_countries=["US"],
            usual_devices=["device-1"],
            usual_hours=[8, 9],
        )
    )
    db_session.commit()

    assert updated.usual_countries == ["US"]
    assert repository.get_by_user_id("user-1") is updated


def test_trusted_login_updates_merge_profile_signals(
    db_session: Session,
) -> None:
    repository = UserProfileRepository(db_session)

    repository.add_trusted_login(
        user_id="user-1",
        device_id="device-1",
        country="us",
        hour=8,
    )
    db_session.commit()
    repository.add_trusted_login(
        user_id="user-1",
        device_id="device-2",
        country="US",
        hour=9,
    )
    db_session.commit()

    profile = repository.get_by_user_id("user-1")

    assert profile is not None
    assert profile.usual_devices == ["device-1", "device-2"]
    assert profile.usual_countries == ["US"]
    assert profile.usual_hours == [8, 9]
