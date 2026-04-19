from datetime import datetime, timezone

import pytest

from app.services.user_service import UserService
from tests.helpers import make_user


class FakeUserRepository:
    def __init__(self, user) -> None:
        self.user = user
        self.touch_calls = 0

    async def get_by_telegram_id(self, telegram_id: int):
        if self.user is None:
            return None
        if self.user.telegram_id != telegram_id:
            return None
        return self.user

    async def touch_last_interaction(self, user):
        self.touch_calls += 1
        user.last_interaction_at = datetime(2026, 4, 19, 19, 0, tzinfo=timezone.utc)
        return user


@pytest.mark.asyncio
async def test_touch_last_interaction_updates_separate_field_and_commits(dummy_session) -> None:
    user = make_user(last_interaction_at=None)
    user_repository = FakeUserRepository(user)
    service = UserService(
        session=dummy_session,
        user_repository=user_repository,
    )

    await service.touch_last_interaction(user.telegram_id)

    assert user_repository.touch_calls == 1
    assert user.last_interaction_at == datetime(2026, 4, 19, 19, 0, tzinfo=timezone.utc)
    assert dummy_session.commit_calls == 1
