from datetime import date, datetime, time, timezone

import pytest

from app.services.reminder_service import ReminderService
from tests.helpers import make_habit, make_user


class FakeHabitRepository:
    def __init__(self, habits) -> None:
        self.habits = habits

    async def get_habits_for_reminder_check(self):
        return list(self.habits)


class FakeHabitLogRepository:
    def __init__(self, completed_pairs) -> None:
        self.completed_pairs = set(completed_pairs)

    async def is_completed_for_date(self, habit_id: int, completed_for_date: date) -> bool:
        return (habit_id, completed_for_date) in self.completed_pairs


@pytest.mark.asyncio
async def test_due_reminder_logic_filters_out_completed_paused_and_non_matching_habits() -> None:
    current_utc_datetime = datetime(2026, 4, 4, 18, 35, 42, tzinfo=timezone.utc)
    local_date = date(2026, 4, 4)

    due_habit = make_habit(
        id=1,
        title="Drink water",
        reminder_enabled=True,
        reminder_time=time(21, 35),
        user=make_user(telegram_id=101, utc_offset_minutes=180),
    )
    completed_habit = make_habit(
        id=2,
        title="Read",
        reminder_enabled=True,
        reminder_time=time(21, 35),
        user=make_user(telegram_id=102, utc_offset_minutes=180),
    )
    paused_habit = make_habit(
        id=3,
        title="Stretch",
        reminder_enabled=True,
        reminder_time=time(21, 35),
        is_paused=True,
        paused_at=datetime(2026, 4, 4, 9, 0, tzinfo=timezone.utc),
        user=make_user(telegram_id=103, utc_offset_minutes=180),
    )
    different_time_habit = make_habit(
        id=4,
        title="Walk",
        reminder_enabled=True,
        reminder_time=time(21, 40),
        user=make_user(telegram_id=104, utc_offset_minutes=180),
    )
    not_due_today_habit = make_habit(
        id=5,
        title="Journal",
        frequency_type="interval",
        frequency_interval=2,
        start_date=date(2026, 4, 3),
        reminder_enabled=True,
        reminder_time=time(21, 35),
        user=make_user(telegram_id=105, utc_offset_minutes=180),
    )

    service = ReminderService(
        habit_repository=FakeHabitRepository(
            [due_habit, completed_habit, paused_habit, different_time_habit, not_due_today_habit]
        ),
        habit_log_repository=FakeHabitLogRepository({(2, local_date)}),
    )

    result = await service.get_due_habit_reminders(current_utc_datetime)

    assert len(result) == 1
    assert result[0].habit_id == 1
    assert result[0].telegram_id == 101
    assert result[0].habit_title == "Drink water"
