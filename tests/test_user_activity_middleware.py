from types import SimpleNamespace

import pytest

from app.bot.middlewares.user_activity import UserActivityMiddleware


class FakeEvent:
    def __init__(self, telegram_id: int | None) -> None:
        self.from_user = (
            SimpleNamespace(id=telegram_id) if telegram_id is not None else None
        )


@pytest.mark.asyncio
async def test_user_activity_middleware_touches_known_event() -> None:
    calls: list[int] = []
    middleware = UserActivityMiddleware(activity_toucher=lambda telegram_id: _touch(calls, telegram_id))
    event = FakeEvent(telegram_id=501)
    handled = False

    async def handler(event, data):
        nonlocal handled
        handled = True
        return "ok"

    result = await middleware(handler, event, {})

    assert result == "ok"
    assert handled is True
    assert calls == [501]


@pytest.mark.asyncio
async def test_user_activity_middleware_skips_events_without_user() -> None:
    calls: list[int] = []
    middleware = UserActivityMiddleware(activity_toucher=lambda telegram_id: _touch(calls, telegram_id))
    event = FakeEvent(telegram_id=None)

    async def handler(event, data):
        return "ok"

    result = await middleware(handler, event, {})

    assert result == "ok"
    assert calls == []


async def _touch(calls: list[int], telegram_id: int) -> None:
    calls.append(telegram_id)
