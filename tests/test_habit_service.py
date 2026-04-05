from datetime import date, datetime, time, timezone

import pytest

from app.services.habit_service import (
    HabitDeletedError,
    HabitNotDueTodayError,
    HabitService,
    HabitValidationError,
)
from app.services.habit_schedule_service import HabitScheduleService
from tests.helpers import make_habit


class FakeHabitRepository:
    def __init__(self, habit=None, active_habits=None) -> None:
        self.habit = habit
        self.active_habits = list(active_habits or [])
        self.create_called = False
        self.archive_called = False
        self.restore_called = False
        self.soft_delete_called = False

    async def create_habit(
        self,
        user_id: int,
        title: str,
        *,
        frequency_type: str = "daily",
        frequency_interval: int | None = None,
        week_days_mask: int | None = None,
        start_date: date | None = None,
        reminder_enabled: bool = False,
        reminder_time: time | None = None,
    ):
        self.create_called = True
        self.habit = make_habit(
            id=11,
            user_id=user_id,
            title=title,
            frequency_type=frequency_type,
            frequency_interval=frequency_interval,
            week_days_mask=week_days_mask,
            start_date=start_date or date.today(),
            reminder_enabled=reminder_enabled,
            reminder_time=reminder_time,
        )
        return self.habit

    async def get_habit_by_id_for_user(self, habit_id: int, user_id: int):
        if self.habit is None or self.habit.id != habit_id or self.habit.user_id != user_id:
            return None
        return self.habit

    async def get_active_habits_by_user(self, user_id: int):
        return [habit for habit in self.active_habits if habit.user_id == user_id]

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

    async def update_last_completed_at(self, habit, last_completed_at: datetime):
        habit.last_completed_at = last_completed_at
        return habit


class FakeHabitLogRepository:
    def __init__(self, completed_dates=None, completed_today_ids=None) -> None:
        self.completed_dates = completed_dates or {}
        self.completed_today_ids = set(completed_today_ids or [])
        self.created_logs: list[tuple[int, date]] = []

    async def is_completed_for_date(self, habit_id: int, completed_for_date: date) -> bool:
        return completed_for_date in self.completed_dates.get(habit_id, [])

    async def create_log(self, habit_id: int, completed_for_date: date):
        self.created_logs.append((habit_id, completed_for_date))
        self.completed_dates.setdefault(habit_id, []).append(completed_for_date)

    async def get_completion_dates(self, habit_id: int) -> list[date]:
        return sorted(self.completed_dates.get(habit_id, []))

    async def get_completed_habit_ids_for_user_by_date(self, user_id: int, target_date: date) -> list[int]:
        return list(self.completed_today_ids)

    async def count_completed_today_for_user(self, user_id: int, target_date: date) -> int:
        return len(self.completed_today_ids)


def build_service(dummy_session, habit=None, active_habits=None, completed_dates=None, completed_today_ids=None) -> HabitService:
    return HabitService(
        session=dummy_session,
        habit_repository=FakeHabitRepository(habit, active_habits),
        habit_log_repository=FakeHabitLogRepository(
            completed_dates=completed_dates,
            completed_today_ids=completed_today_ids,
        ),
    )


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
async def test_create_habit_saves_every_other_day_schedule(dummy_session) -> None:
    service = build_service(dummy_session)

    habit = await service.create_habit(
        1,
        "Walk",
        frequency_type=HabitScheduleService.INTERVAL,
        frequency_interval=2,
        reminder_enabled=True,
        reminder_time=time(9, 30),
        start_date=date(2026, 4, 4),
    )

    assert habit.frequency_type == "interval"
    assert habit.frequency_interval == 2
    assert habit.week_days_mask is None
    assert habit.reminder_enabled is True
    assert habit.reminder_time == time(9, 30)


@pytest.mark.asyncio
async def test_get_today_habits_returns_only_due_habits(dummy_session, monkeypatch) -> None:
    target_date = date(2026, 4, 4)
    weekdays_mask = HabitScheduleService.build_week_days_mask([0, 2, 4])
    daily_habit = make_habit(id=1, user_id=1, title="Daily", start_date=date(2026, 4, 1))
    interval_habit = make_habit(
        id=2,
        user_id=1,
        title="Interval",
        frequency_type="interval",
        frequency_interval=2,
        start_date=date(2026, 4, 4),
    )
    weekdays_habit = make_habit(
        id=3,
        user_id=1,
        title="Weekdays",
        frequency_type="weekdays",
        week_days_mask=weekdays_mask,
        start_date=date(2026, 4, 1),
    )
    service = build_service(
        dummy_session,
        active_habits=[daily_habit, interval_habit, weekdays_habit],
        completed_today_ids=[1],
    )
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    result = await service.get_today_habits(1)

    assert [item.id for item in result] == [1, 2]
    assert result[0].is_completed_today is True
    assert result[1].is_completed_today is False


@pytest.mark.asyncio
async def test_complete_habit_rejects_when_not_due_today(dummy_session, monkeypatch) -> None:
    target_date = date(2026, 4, 4)
    weekdays_mask = HabitScheduleService.build_week_days_mask([0, 2, 4])
    habit = make_habit(
        id=5,
        user_id=1,
        frequency_type="weekdays",
        week_days_mask=weekdays_mask,
        start_date=date(2026, 4, 1),
    )
    service = build_service(dummy_session, habit=habit)
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    with pytest.raises(HabitNotDueTodayError):
        await service.complete_habit_for_today(1, 5)


@pytest.mark.asyncio
async def test_archive_habit_marks_inactive_and_commits(dummy_session) -> None:
    habit = make_habit(id=5, user_id=1, is_active=True)
    service = build_service(dummy_session, habit=habit)

    result = await service.archive_habit(1, 5)

    assert result is True
    assert habit.is_active is False
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_restore_habit_marks_active_and_commits(dummy_session) -> None:
    habit = make_habit(id=5, user_id=1, is_active=False)
    service = build_service(dummy_session, habit=habit)

    result = await service.restore_habit(1, 5)

    assert result is True
    assert habit.is_active is True
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_soft_delete_habit_marks_deleted_and_commits(dummy_session) -> None:
    habit = make_habit(id=8, user_id=1, is_active=True, is_deleted=False)
    service = build_service(dummy_session, habit=habit)

    result = await service.soft_delete_habit(1, 8)

    assert result is True
    assert habit.is_active is False
    assert habit.is_deleted is True
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_soft_delete_habit_rejects_already_deleted(dummy_session) -> None:
    habit = make_habit(id=8, user_id=1, is_active=False, is_deleted=True)
    service = build_service(dummy_session, habit=habit)

    with pytest.raises(HabitDeletedError):
        await service.soft_delete_habit(1, 8)
