from types import SimpleNamespace

import pytest

import app.bot.middlewares.blocked_user as blocked_user_module
from app.bot.middlewares.blocked_user import BLOCKED_USER_TEXT, BlockedUserMiddleware
from tests.helpers import make_user


class FakeMessage:
    def __init__(self, telegram_id: int | None) -> None:
        self.from_user = (
            SimpleNamespace(id=telegram_id) if telegram_id is not None else None
        )
        self.answer_calls: list[dict[str, object]] = []

    async def answer(self, text: str, **kwargs) -> None:
        payload = {"text": text}
        payload.update(kwargs)
        self.answer_calls.append(payload)


class FakeCallbackQuery:
    def __init__(self, telegram_id: int | None) -> None:
        self.from_user = (
            SimpleNamespace(id=telegram_id) if telegram_id is not None else None
        )
        self.answer_calls: list[dict[str, object]] = []

    async def answer(self, text: str, **kwargs) -> None:
        payload = {"text": text}
        payload.update(kwargs)
        self.answer_calls.append(payload)


@pytest.mark.asyncio
async def test_blocked_user_middleware_blocks_messages(monkeypatch) -> None:
    monkeypatch.setattr(blocked_user_module, "Message", FakeMessage)
    monkeypatch.setattr(blocked_user_module, "CallbackQuery", FakeCallbackQuery)
    middleware = BlockedUserMiddleware(
        user_loader=_build_user_loader(make_user(is_blocked=True))
    )
    event = FakeMessage(telegram_id=101)
    handled = False

    async def handler(event, data):
        nonlocal handled
        handled = True
        return "ok"

    result = await middleware(handler, event, {})

    assert result is None
    assert handled is False
    assert event.answer_calls == [{"text": BLOCKED_USER_TEXT}]


@pytest.mark.asyncio
async def test_blocked_user_middleware_blocks_callbacks(monkeypatch) -> None:
    monkeypatch.setattr(blocked_user_module, "Message", FakeMessage)
    monkeypatch.setattr(blocked_user_module, "CallbackQuery", FakeCallbackQuery)
    middleware = BlockedUserMiddleware(
        user_loader=_build_user_loader(make_user(is_blocked=True))
    )
    event = FakeCallbackQuery(telegram_id=202)
    handled = False

    async def handler(event, data):
        nonlocal handled
        handled = True
        return "ok"

    result = await middleware(handler, event, {})

    assert result is None
    assert handled is False
    assert event.answer_calls == [
        {"text": BLOCKED_USER_TEXT, "show_alert": True}
    ]


@pytest.mark.asyncio
async def test_blocked_user_middleware_allows_unknown_user(monkeypatch) -> None:
    monkeypatch.setattr(blocked_user_module, "Message", FakeMessage)
    monkeypatch.setattr(blocked_user_module, "CallbackQuery", FakeCallbackQuery)
    middleware = BlockedUserMiddleware(user_loader=_build_user_loader(None))
    event = FakeMessage(telegram_id=303)
    handled = False

    async def handler(event, data):
        nonlocal handled
        handled = True
        return "ok"

    result = await middleware(handler, event, {})

    assert result == "ok"
    assert handled is True
    assert event.answer_calls == []


def _build_user_loader(user):
    async def load_user(telegram_id: int):
        return user

    return load_user
