from datetime import date, datetime, timezone

import pytest

from app.services.habit_schedule_service import HabitScheduleService
from app.services.progress_service import ProgressService
from tests.helpers import make_habit


class FakeHabitRepository:
    def __init__(self, active_habits, last_completed_habits) -> None:
        self.active_habits = list(active_habits)
        self.last_completed_habits = list(last_completed_habits)

    async def get_active_habits_by_user(self, user_id: int):
        return list(self.active_habits)

    async def get_last_completed_habits_by_user(self, user_id: int, *, limit: int = 1):
        return list(self.last_completed_habits)[:limit]


class FakeHabitLogRepository:
    def __init__(self, completion_rows) -> None:
        self.completion_rows = list(completion_rows)

    async def get_completed_habit_ids_for_user_by_date(self, user_id: int, target_date: date):
        return [
            habit_id
            for habit_id, completed_for_date in self.completion_rows
            if completed_for_date == target_date
        ]

    async def get_completion_dates_for_habit_ids(self, habit_ids: list[int]):
        habit_ids_set = set(habit_ids)
        return [
            row
            for row in self.completion_rows
            if row[0] in habit_ids_set
        ]


def build_service() -> ProgressService:
    weekdays_mask = HabitScheduleService.build_week_days_mask([0, 2, 4])

    daily_habit = make_habit(
        id=1,
        title="Зарядка",
        start_date=date(2026, 3, 29),
        last_completed_at=datetime(2026, 3, 31, 8, 0, tzinfo=timezone.utc),
    )
    interval_habit = make_habit(
        id=2,
        title="Прогулка",
        frequency_type="interval",
        frequency_interval=2,
        start_date=date(2026, 3, 29),
        last_completed_at=datetime(2026, 4, 4, 9, 30, tzinfo=timezone.utc),
    )
    weekdays_habit = make_habit(
        id=3,
        title="Чтение",
        frequency_type="weekdays",
        week_days_mask=weekdays_mask,
        start_date=date(2026, 3, 29),
        last_completed_at=datetime(2026, 4, 1, 19, 0, tzinfo=timezone.utc),
    )

    completion_rows = [
        (1, date(2026, 3, 29)),
        (1, date(2026, 3, 30)),
        (1, date(2026, 3, 31)),
        (2, date(2026, 3, 31)),
        (2, date(2026, 4, 2)),
        (2, date(2026, 4, 4)),
        (3, date(2026, 4, 1)),
    ]

    return ProgressService(
        session=None,
        habit_repository=FakeHabitRepository(
            active_habits=[daily_habit, interval_habit, weekdays_habit],
            last_completed_habits=[interval_habit, weekdays_habit, daily_habit],
        ),
        habit_log_repository=FakeHabitLogRepository(completion_rows),
    )


@pytest.mark.asyncio
async def test_completion_rate_for_seven_days_uses_due_occurrences() -> None:
    service = build_service()

    result = await service.get_completion_rate(1, 7, date(2026, 4, 4))

    assert result.completed == 7
    assert result.total_possible == 14
    assert result.percentage == 50.0


@pytest.mark.asyncio
async def test_completion_rate_for_thirty_days_uses_schedule_denominator() -> None:
    service = build_service()

    result = await service.get_completion_rate(1, 30, date(2026, 4, 4))

    assert result.completed == 7
    assert result.total_possible == 14
    assert result.percentage == 50.0


@pytest.mark.asyncio
async def test_progress_screen_data_aggregates_schedule_aware_values() -> None:
    service = build_service()

    result = await service.get_progress_screen_data(1, date(2026, 4, 4))

    assert result.active_habits_count == 3
    assert result.due_today_count == 2
    assert result.completed_today_count == 1
    assert result.remaining_today_count == 1
    assert result.completion_rate_7_days == 50.0
    assert result.completion_rate_30_days == 50.0
    assert result.best_current_streak_habit_title == "Прогулка"
    assert result.best_current_streak_value == 3
    assert result.last_completed_habit_title == "Прогулка"
    assert result.last_completed_at == datetime(2026, 4, 4, 9, 30, tzinfo=timezone.utc)
