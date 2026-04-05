from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.progress_service import ProgressService
from tests.helpers import make_habit


class FakeHabitRepository:
    def __init__(self, active_habits, last_completed_habits) -> None:
        self.active_habits = active_habits
        self.last_completed_habits = last_completed_habits

    async def count_active_habits(self, user_id: int) -> int:
        return len(self.active_habits)

    async def get_active_habits_by_user(self, user_id: int):
        return list(self.active_habits)

    async def get_last_completed_habits_by_user(self, user_id: int, *, limit: int = 1):
        return list(self.last_completed_habits)[:limit]


class FakeHabitLogRepository:
    def __init__(self, period_counts, completion_rows, completion_counts_by_habit) -> None:
        self.period_counts = period_counts
        self.completion_rows = completion_rows
        self.completion_counts_by_habit = completion_counts_by_habit

    async def count_completed_by_user_for_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        *,
        active_only: bool = True,
    ) -> int:
        return self.period_counts[(start_date, end_date, active_only)]

    async def get_completion_dates_for_habit_ids(self, habit_ids: list[int]):
        return [
            row
            for row in self.completion_rows
            if row[0] in habit_ids
        ]

    async def get_completion_counts_by_habit_for_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        *,
        active_only: bool = True,
    ):
        return list(self.completion_counts_by_habit)


def build_service(target_date: date) -> ProgressService:
    habit_one = make_habit(
        id=1,
        title="Read",
        last_completed_at=datetime(2026, 4, 4, 9, 30, tzinfo=timezone.utc),
    )
    habit_two = make_habit(
        id=2,
        title="Walk",
        last_completed_at=datetime(2026, 4, 3, 18, 0, tzinfo=timezone.utc),
    )
    week_start = target_date - timedelta(days=6)
    thirty_day_start = target_date - timedelta(days=29)

    period_counts = {
        (target_date, target_date, True): 1,
        (week_start, target_date, True): 9,
        (thirty_day_start, target_date, True): 24,
    }
    completion_rows = [
        (1, target_date - timedelta(days=2)),
        (1, target_date - timedelta(days=1)),
        (1, target_date),
        (2, target_date - timedelta(days=6)),
    ]
    completion_counts_by_habit = [
        (1, "Read", 7),
        (2, "Walk", 2),
    ]
    return ProgressService(
        session=None,
        habit_repository=FakeHabitRepository(
            active_habits=[habit_one, habit_two],
            last_completed_habits=[habit_one, habit_two],
        ),
        habit_log_repository=FakeHabitLogRepository(
            period_counts=period_counts,
            completion_rows=completion_rows,
            completion_counts_by_habit=completion_counts_by_habit,
        ),
    )


@pytest.mark.asyncio
async def test_completion_rate_for_seven_days() -> None:
    target_date = date(2026, 4, 4)
    service = build_service(target_date)

    result = await service.get_completion_rate(1, 7, target_date)

    assert result.completed == 9
    assert result.total_possible == 14
    assert result.percentage == 64.3


@pytest.mark.asyncio
async def test_completion_rate_for_thirty_days() -> None:
    target_date = date(2026, 4, 4)
    service = build_service(target_date)

    result = await service.get_completion_rate(1, 30, target_date)

    assert result.completed == 24
    assert result.total_possible == 60
    assert result.percentage == 40.0


@pytest.mark.asyncio
async def test_progress_screen_data_aggregates_expected_values() -> None:
    target_date = date(2026, 4, 4)
    service = build_service(target_date)

    result = await service.get_progress_screen_data(1, target_date)

    assert result.active_habits_count == 2
    assert result.completed_today_count == 1
    assert result.remaining_today_count == 1
    assert result.completion_rate_7_days == 64.3
    assert result.completion_rate_30_days == 40.0
    assert result.best_current_streak_habit_title == "Read"
    assert result.best_current_streak_value == 3
    assert result.last_completed_habit_title == "Read"
    assert result.last_completed_at == datetime(2026, 4, 4, 9, 30, tzinfo=timezone.utc)
