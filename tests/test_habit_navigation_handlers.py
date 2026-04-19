from datetime import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.callbacks import (
    HabitGoalActionCallback,
    HabitReminderCancelCallback,
    HabitReminderDisableCallback,
    HabitReturnTarget,
)
from app.bot.handlers.edit_habit import save_habit_title as save_edited_habit_title
from app.bot.handlers.habit_goals import clear_goal
from app.bot.handlers.reminders import (
    cancel_reminder_setup,
    disable_reminder,
    save_reminder_time,
)
from app.bot.habit_text import build_habit_card_text, build_habit_edit_menu_text
from app.services.habit_goal_service import HabitGoalProgress
from app.services.habit_service import HabitCard, HabitReminderState


class FakeState:
    def __init__(self, data: dict | None = None) -> None:
        self.data = dict(data or {})
        self.cleared = False
        self.state = None

    async def clear(self) -> None:
        self.data.clear()
        self.cleared = True

    async def get_data(self) -> dict:
        return dict(self.data)

    async def set_state(self, value) -> None:
        self.state = value

    async def update_data(self, **kwargs) -> None:
        self.data.update(kwargs)


def _make_habit_card(
    *,
    title: str = "Читать",
    reminder_enabled: bool = False,
    reminder_time_value: time | None = None,
    goal: HabitGoalProgress | None = None,
) -> HabitCard:
    return HabitCard(
        id=5,
        title=title,
        is_completed_today=False,
        is_due_today=True,
        total_completions=8,
        current_streak=4,
        best_streak=9,
        is_active=True,
        reminder_enabled=reminder_enabled,
        reminder_time=reminder_time_value,
        frequency_text="ежедневно",
        goal=goal,
    )


def _make_user_service():
    return SimpleNamespace(
        get_by_telegram_id=AsyncMock(return_value=SimpleNamespace(id=1)),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("return_to", "expected_builder"),
    [
        (HabitReturnTarget.CARD.value, build_habit_card_text),
        (HabitReturnTarget.EDIT.value, build_habit_edit_menu_text),
    ],
)
async def test_save_reminder_time_returns_by_context(return_to, expected_builder) -> None:
    bot = SimpleNamespace(
        edit_message_text=AsyncMock(),
        send_message=AsyncMock(),
    )
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=101),
        text="09:30",
        bot=bot,
        answer=AsyncMock(),
    )
    state = FakeState(
        {
            "habit_id": 5,
            "source": "list",
            "return_to": return_to,
            "mode": "enable",
            "prompt_chat_id": 10,
            "prompt_message_id": 20,
        }
    )
    habit_card = _make_habit_card(
        reminder_enabled=True,
        reminder_time_value=time(9, 30),
    )
    habit_service = SimpleNamespace(
        enable_reminder=AsyncMock(
            return_value=HabitReminderState(enabled=True, reminder_time=time(9, 30))
        ),
        update_reminder_time=AsyncMock(),
        get_habit_card=AsyncMock(return_value=habit_card),
    )

    await save_reminder_time(
        message,
        state,
        _make_user_service(),
        habit_service,
    )

    assert state.cleared is True
    bot.edit_message_text.assert_awaited_once()
    assert bot.edit_message_text.await_args.kwargs["text"] == expected_builder(habit_card)
    message.answer.assert_awaited_once_with("Буду напоминать в 09:30.")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("return_to", "expected_builder"),
    [
        (HabitReturnTarget.CARD.value, build_habit_card_text),
        (HabitReturnTarget.EDIT.value, build_habit_edit_menu_text),
    ],
)
async def test_cancel_reminder_setup_returns_by_context(return_to, expected_builder) -> None:
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=101),
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
    )
    state = FakeState()
    habit_card = _make_habit_card()
    habit_service = SimpleNamespace(get_habit_card=AsyncMock(return_value=habit_card))

    await cancel_reminder_setup(
        callback,
        HabitReminderCancelCallback(
            habit_id=habit_card.id,
            source="list",
            return_to=return_to,
        ),
        state,
        _make_user_service(),
        habit_service,
    )

    assert state.cleared is True
    callback.message.edit_text.assert_awaited_once()
    assert callback.message.edit_text.await_args.args[0] == expected_builder(habit_card)


@pytest.mark.asyncio
async def test_disable_reminder_returns_to_edit_menu() -> None:
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=101),
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
    )
    habit_card = _make_habit_card()
    habit_service = SimpleNamespace(
        disable_reminder=AsyncMock(
            return_value=HabitReminderState(enabled=False, reminder_time=None)
        ),
        get_habit_card=AsyncMock(return_value=habit_card),
    )

    await disable_reminder(
        callback,
        HabitReminderDisableCallback(
            habit_id=habit_card.id,
            source="list",
            return_to=HabitReturnTarget.EDIT.value,
        ),
        _make_user_service(),
        habit_service,
    )

    callback.message.edit_text.assert_awaited_once()
    assert callback.message.edit_text.await_args.args[0] == build_habit_edit_menu_text(
        habit_card
    )


@pytest.mark.asyncio
async def test_clear_goal_returns_to_edit_menu() -> None:
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=101),
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
    )
    habit_card = _make_habit_card()
    habit_service = SimpleNamespace(clear_habit_goal=AsyncMock(return_value=habit_card))

    await clear_goal(
        callback,
        HabitGoalActionCallback(
            action="clear",
            habit_id=habit_card.id,
            source="list",
            return_to=HabitReturnTarget.EDIT.value,
        ),
        FakeState(),
        _make_user_service(),
        habit_service,
    )

    callback.message.edit_text.assert_awaited_once()
    assert callback.message.edit_text.await_args.args[0] == build_habit_edit_menu_text(
        habit_card
    )


@pytest.mark.asyncio
async def test_edit_title_save_returns_to_edit_menu() -> None:
    bot = SimpleNamespace(
        edit_message_text=AsyncMock(),
        send_message=AsyncMock(),
    )
    message = SimpleNamespace(
        from_user=SimpleNamespace(id=101),
        text="Новая привычка",
        bot=bot,
        answer=AsyncMock(),
    )
    state = FakeState(
        {
            "habit_id": 5,
            "source": "list",
            "prompt_chat_id": 10,
            "prompt_message_id": 20,
        }
    )
    habit_card = _make_habit_card(title="Новая привычка")
    habit_service = SimpleNamespace(rename_habit=AsyncMock(return_value=habit_card))

    await save_edited_habit_title(
        message,
        state,
        _make_user_service(),
        habit_service,
    )

    assert state.cleared is True
    bot.edit_message_text.assert_awaited_once()
    assert bot.edit_message_text.await_args.kwargs["text"] == build_habit_edit_menu_text(
        habit_card
    )
    message.answer.assert_awaited_once_with("Название обновил: «Новая привычка».")
