from datetime import date, datetime, timedelta, timezone

import pytest

from app.services.habit_service import (
    HabitDeletedError,
    HabitService,
    HabitValidationError,
)
from tests.helpers import make_habit


class FakeHabitRepository:
    def __init__(self, habit=None) -> None:
        self.habit = habit
        self.create_called = False
        self.archive_called = False
        self.restore_called = False
        self.soft_delete_called = False

    async def create_habit(self, user_id: int, title: str, frequency_type: str = "daily"):
        self.create_called = True
        self.habit = make_habit(
            id=11,
            user_id=user_id,
            title=title,
            frequency_type=frequency_type,
        )
        return self.habit

    async def get_habit_by_id_for_user(self, habit_id: int, user_id: int):
        if self.habit is None or self.habit.id != habit_id or self.habit.user_id != user_id:
            return None
        return self.habit

    async def update_title(self, habit, title: str):
        habit.title = title
        return habit

    async def archive_habit(self, habit):
        self.archive_called = True
        habit.is_active = False
        return habit

    async def restore_habit(self, habit):
        self.restore_called = True
        habit.is_active = True
        return habit

    async def soft_delete_habit(self, habit):
        self.soft_delete_called = True
        habit.is_active = False
        habit.is_deleted = True
        habit.deleted_at = datetime.now(timezone.utc)
        return habit


class FakeHabitLogRepository:
    async def is_completed_for_date(self, habit_id: int, completed_for_date: date) -> bool:
        return False

    async def count_completions(self, habit_id: int) -> int:
        return 0

    async def get_completion_dates(self, habit_id: int) -> list[date]:
        return []

    async def get_completed_habit_ids_for_user_by_date(self, user_id: int, target_date: date) -> list[int]:
        return []

    async def count_completed_today_for_user(self, user_id: int, target_date: date) -> int:
        return 0


def build_service(dummy_session, habit=None) -> HabitService:
    return HabitService(
        session=dummy_session,
        habit_repository=FakeHabitRepository(habit),
        habit_log_repository=FakeHabitLogRepository(),
    )


def test_current_streak_counts_today_and_previous_days() -> None:
    today = date(2026, 4, 4)
    completion_dates = {
        today,
        today - timedelta(days=1),
        today - timedelta(days=2),
    }

    result = HabitService._calculate_current_streak(completion_dates, today)

    assert result == 3


def test_current_streak_can_continue_from_yesterday() -> None:
    today = date(2026, 4, 4)
    completion_dates = {
        today - timedelta(days=1),
        today - timedelta(days=2),
        today - timedelta(days=3),
    }

    result = HabitService._calculate_current_streak(completion_dates, today)

    assert result == 3


def test_best_streak_returns_longest_run() -> None:
    completion_dates = [
        date(2026, 3, 20),
        date(2026, 3, 21),
        date(2026, 3, 22),
        date(2026, 3, 25),
        date(2026, 3, 26),
    ]

    result = HabitService._calculate_best_streak(completion_dates)

    assert result == 3


@pytest.mark.asyncio
async def test_create_habit_rejects_empty_title(dummy_session) -> None:
    service = build_service(dummy_session)

    with pytest.raises(HabitValidationError):
        await service.create_habit(1, "   ")


@pytest.mark.asyncio
async def test_create_habit_rejects_too_long_title(dummy_session) -> None:
    service = build_service(dummy_session)

    with pytest.raises(HabitValidationError):
        await service.create_habit(1, "x" * 101)


@pytest.mark.asyncio
async def test_archive_habit_marks_inactive_and_commits(dummy_session) -> None:
    habit = make_habit(id=5, user_id=1, is_active=True)
    service = build_service(dummy_session, habit)

    result = await service.archive_habit(1, 5)

    assert result is True
    assert habit.is_active is False
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_restore_habit_marks_active_and_commits(dummy_session) -> None:
    habit = make_habit(id=5, user_id=1, is_active=False)
    service = build_service(dummy_session, habit)

    result = await service.restore_habit(1, 5)

    assert result is True
    assert habit.is_active is True
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_soft_delete_habit_marks_deleted_and_commits(dummy_session) -> None:
    habit = make_habit(id=8, user_id=1, is_active=True, is_deleted=False)
    service = build_service(dummy_session, habit)

    result = await service.soft_delete_habit(1, 8)

    assert result is True
    assert habit.is_active is False
    assert habit.is_deleted is True
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_soft_delete_habit_rejects_already_deleted(dummy_session) -> None:
    habit = make_habit(id=8, user_id=1, is_active=False, is_deleted=True)
    service = build_service(dummy_session, habit)

    with pytest.raises(HabitDeletedError):
        await service.soft_delete_habit(1, 8)
