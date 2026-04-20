from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.callbacks import AdminBroadcastCallback, AdminUserActionCallback
from app.bot.handlers.admin import (
    AdminStates,
    _build_block_confirmation_text,
    _build_broadcast_confirmation_text,
    _build_dashboard_text,
    _build_user_card_text,
    handle_admin_broadcast_callback,
    handle_admin_user_action,
    receive_admin_broadcast_photo,
    receive_admin_broadcast_text,
)
from app.services.admin_service import AdminDashboardData, AdminUserCard
from app.services.broadcast_service import (
    BROADCAST_AUDIENCE_ACTIVE,
    BROADCAST_TYPE_PHOTO,
    BROADCAST_TYPE_TEXT,
    BroadcastPreview,
)


class FakeState:
    def __init__(self, data: dict | None = None) -> None:
        self.data = dict(data or {})
        self.state = None
        self.cleared = False

    async def clear(self) -> None:
        self.data.clear()
        self.state = None
        self.cleared = True

    async def get_data(self) -> dict:
        return dict(self.data)

    async def set_state(self, value) -> None:
        self.state = getattr(value, "state", value)

    async def update_data(self, **kwargs) -> None:
        self.data.update(kwargs)


def _make_user_card(**overrides) -> AdminUserCard:
    defaults = {
        "id": 2,
        "telegram_id": 7002,
        "username": "reader",
        "full_name": "Иван Петров",
        "is_admin": False,
        "is_blocked": False,
        "active_habits_count": 3,
        "archived_habits_count": 1,
        "deleted_habits_count": 0,
        "created_at": datetime(2026, 4, 20, 10, 0, tzinfo=timezone.utc),
        "last_completed_habit_title": "Чтение",
        "last_completed_at": datetime(2026, 4, 19, 8, 30, tzinfo=timezone.utc),
    }
    defaults.update(overrides)
    return AdminUserCard(**defaults)


def _make_callback(*, user_id: int = 7001):
    message = SimpleNamespace(
        chat=SimpleNamespace(id=15),
        message_id=25,
        edit_text=AsyncMock(),
    )
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        message=message,
        answer=AsyncMock(),
        bot=SimpleNamespace(),
    )


def _make_message(
    *,
    user_id: int = 7001,
    text: str | None = None,
    caption: str | None = None,
    photo=None,
    bot=None,
):
    return SimpleNamespace(
        from_user=SimpleNamespace(id=user_id),
        text=text,
        caption=caption,
        photo=photo,
        bot=bot
        or SimpleNamespace(
            edit_message_text=AsyncMock(),
            send_message=AsyncMock(),
        ),
        answer=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_handle_admin_user_action_opens_block_confirmation() -> None:
    callback = _make_callback()
    state = FakeState({"keep": "value"})
    user_card = _make_user_card()
    admin_service = SimpleNamespace(get_user_card=AsyncMock(return_value=user_card))

    await handle_admin_user_action(
        callback,
        AdminUserActionCallback(action="ask_block", user_id=user_card.id),
        state,
        admin_service,
    )

    assert state.cleared is False
    callback.message.edit_text.assert_awaited_once()
    assert callback.message.edit_text.await_args.args[0] == _build_block_confirmation_text(
        user_card
    )
    callback.answer.assert_awaited_once_with()
    admin_service.get_user_card.assert_awaited_once_with(callback.from_user.id, user_card.id)


@pytest.mark.asyncio
async def test_handle_admin_user_action_blocks_user_and_returns_card() -> None:
    callback = _make_callback()
    state = FakeState({"step": "confirm"})
    blocked_user_card = _make_user_card(is_blocked=True)
    admin_service = SimpleNamespace(block_user=AsyncMock(return_value=blocked_user_card))

    await handle_admin_user_action(
        callback,
        AdminUserActionCallback(action="block", user_id=blocked_user_card.id),
        state,
        admin_service,
    )

    assert state.cleared is True
    callback.message.edit_text.assert_awaited_once()
    assert callback.message.edit_text.await_args.args[0] == _build_user_card_text(
        blocked_user_card
    )
    callback.answer.assert_awaited_once_with("Пользователь заблокирован.")
    admin_service.block_user.assert_awaited_once_with(
        callback.from_user.id,
        blocked_user_card.id,
    )


@pytest.mark.asyncio
async def test_handle_admin_broadcast_callback_cancel_returns_dashboard() -> None:
    callback = _make_callback()
    state = FakeState({"broadcast_type": "text"})
    dashboard = AdminDashboardData(
        total_users_count=12,
        admin_users_count=2,
        blocked_users_count=1,
        deleted_habits_count=3,
        unread_feedback_count=4,
    )
    admin_service = SimpleNamespace(get_dashboard=AsyncMock(return_value=dashboard))
    broadcast_service = SimpleNamespace(send_broadcast=AsyncMock())

    await handle_admin_broadcast_callback(
        callback,
        AdminBroadcastCallback(action="cancel"),
        state,
        admin_service,
        broadcast_service,
    )

    assert state.cleared is True
    callback.message.edit_text.assert_awaited_once()
    assert callback.message.edit_text.await_args.args[0] == _build_dashboard_text(dashboard)
    callback.answer.assert_awaited_once_with()
    broadcast_service.send_broadcast.assert_not_awaited()


@pytest.mark.asyncio
async def test_receive_admin_broadcast_text_moves_to_confirmation() -> None:
    preview = BroadcastPreview(
        audience_type=BROADCAST_AUDIENCE_ACTIVE,
        audience_label="Активные пользователи",
        broadcast_type=BROADCAST_TYPE_TEXT,
        format_label="Только текст",
        text="Текст рассылки",
        text_preview="Текст рассылки",
        photo_file_id=None,
        recipients_count=5,
        audience_description="Описание аудитории",
    )
    bot = SimpleNamespace(
        edit_message_text=AsyncMock(),
        send_message=AsyncMock(),
    )
    message = _make_message(user_id=7001, text="  Текст рассылки  ", bot=bot)
    state = FakeState(
        {
            "broadcast_audience_type": BROADCAST_AUDIENCE_ACTIVE,
            "prompt_chat_id": 15,
            "prompt_message_id": 25,
        }
    )
    broadcast_service = SimpleNamespace(prepare_broadcast=AsyncMock(return_value=preview))

    await receive_admin_broadcast_text(message, state, broadcast_service)

    assert state.state == AdminStates.waiting_for_broadcast_confirmation.state
    assert state.data["broadcast_type"] == BROADCAST_TYPE_TEXT
    assert state.data["broadcast_text"] == preview.text
    broadcast_service.prepare_broadcast.assert_awaited_once_with(
        message.from_user.id,
        audience_type=BROADCAST_AUDIENCE_ACTIVE,
        broadcast_type=BROADCAST_TYPE_TEXT,
        text="  Текст рассылки  ",
        photo_file_id=None,
    )
    bot.edit_message_text.assert_awaited_once()
    assert bot.edit_message_text.await_args.kwargs["text"] == _build_broadcast_confirmation_text(
        preview
    )


@pytest.mark.asyncio
async def test_receive_admin_broadcast_photo_without_caption_requests_caption() -> None:
    bot = SimpleNamespace(
        edit_message_text=AsyncMock(),
        send_message=AsyncMock(),
    )
    message = _make_message(
        user_id=7001,
        caption="   ",
        photo=[
            SimpleNamespace(file_id="photo-small"),
            SimpleNamespace(file_id="photo-big"),
        ],
        bot=bot,
    )
    state = FakeState(
        {
            "broadcast_audience_type": BROADCAST_AUDIENCE_ACTIVE,
            "prompt_chat_id": 15,
            "prompt_message_id": 25,
        }
    )
    broadcast_service = SimpleNamespace(prepare_broadcast=AsyncMock())

    await receive_admin_broadcast_photo(message, state, broadcast_service)

    assert state.state == AdminStates.waiting_for_broadcast_caption.state
    assert state.data["broadcast_type"] == BROADCAST_TYPE_PHOTO
    assert state.data["broadcast_photo_file_id"] == "photo-big"
    broadcast_service.prepare_broadcast.assert_not_awaited()
    bot.edit_message_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_admin_broadcast_callback_send_with_incomplete_state_shows_alert() -> None:
    callback = _make_callback()
    state = FakeState({"broadcast_type": BROADCAST_TYPE_TEXT})
    admin_service = SimpleNamespace(get_dashboard=AsyncMock())
    broadcast_service = SimpleNamespace(send_broadcast=AsyncMock())

    await handle_admin_broadcast_callback(
        callback,
        AdminBroadcastCallback(action="send"),
        state,
        admin_service,
        broadcast_service,
    )

    assert state.cleared is True
    callback.message.edit_text.assert_not_awaited()
    callback.answer.assert_awaited_once()
    assert callback.answer.await_args.args[0] == "Не удалось продолжить рассылку. Начни заново."
    assert callback.answer.await_args.kwargs["show_alert"] is True
    broadcast_service.send_broadcast.assert_not_awaited()
