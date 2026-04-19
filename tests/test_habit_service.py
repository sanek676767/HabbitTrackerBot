"""Тесты основных сценариев и пограничных случаев сервиса привычек."""

from datetime import date, datetime, time, timezone

import pytest

from app.services.habit_goal_service import HabitGoalService
from app.services.habit_service import (
    HabitArchivedError,
    HabitDeletedError,
    HabitNotDueTodayError,
    HabitPausedError,
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
        self.pause_called = False
        self.resume_called = False
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
        goal_type: str | None = None,
        goal_target_value: int | None = None,
        goal_achieved_at: datetime | None = None,
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
            goal_type=goal_type,
            goal_target_value=goal_target_value,
            goal_achieved_at=goal_achieved_at,
        )
        return self.habit

    async def get_habit_by_id_for_user(self, habit_id: int, user_id: int):
        if self.habit is None or self.habit.id != habit_id or self.habit.user_id != user_id:
            return None
        return self.habit

    async def get_active_habits_by_user(self, user_id: int):
        return [
            habit
            for habit in self.active_habits
            if habit.user_id == user_id
            and habit.is_active
            and not habit.is_paused
            and not habit.is_deleted
        ]

    async def get_visible_habits_by_user(self, user_id: int):
        return [
            habit
            for habit in self.active_habits
            if habit.user_id == user_id and habit.is_active and not habit.is_deleted
        ]

    async def get_archived_habits_by_user(self, user_id: int):
        return [
            habit
            for habit in self.active_habits
            if habit.user_id == user_id and not habit.is_active and not habit.is_deleted
        ]

    async def update_title(self, habit, title: str):
        habit.title = title
        return habit

    async def update_schedule(
        self,
        habit,
        *,
        frequency_type: str,
        frequency_interval: int | None,
        week_days_mask: int | None,
        start_date: date,
    ):
        habit.frequency_type = frequency_type
        habit.frequency_interval = frequency_interval
        habit.week_days_mask = week_days_mask
        habit.start_date = start_date
        return habit

    async def update_reminder(self, habit, enabled: bool, reminder_time: time | None):
        habit.reminder_enabled = enabled
        habit.reminder_time = reminder_time if enabled else None
        return habit

    async def update_goal(
        self,
        habit,
        *,
        goal_type: str,
        goal_target_value: int,
        goal_achieved_at: datetime | None,
    ):
        habit.goal_type = goal_type
        habit.goal_target_value = goal_target_value
        habit.goal_achieved_at = goal_achieved_at
        return habit

    async def clear_goal(self, habit):
        habit.goal_type = None
        habit.goal_target_value = None
        habit.goal_achieved_at = None
        return habit

    async def update_goal_achieved_at(self, habit, goal_achieved_at: datetime | None):
        habit.goal_achieved_at = goal_achieved_at
        return habit

    async def archive_habit(self, habit):
        self.archive_called = True
        habit.is_active = False
        habit.is_paused = False
        habit.paused_at = None
        return habit

    async def pause_habit(self, habit):
        self.pause_called = True
        habit.is_paused = True
        habit.paused_at = datetime.now(timezone.utc)
        return habit

    async def resume_habit(self, habit):
        self.resume_called = True
        habit.is_paused = False
        habit.paused_at = None
        return habit

    async def restore_habit(self, habit):
        self.restore_called = True
        habit.is_active = True
        return habit

    async def soft_delete_habit(self, habit):
        self.soft_delete_called = True
        habit.is_active = False
        habit.is_paused = False
        habit.is_deleted = True
        habit.paused_at = None
        habit.deleted_at = datetime.now(timezone.utc)
        return habit

    async def update_last_completed_at(self, habit, last_completed_at: datetime):
        habit.last_completed_at = last_completed_at
        return habit

    async def count_active_habits(self, user_id: int) -> int:
        return sum(
            1
            for habit in self.active_habits
            if (
                habit.user_id == user_id
                and habit.is_active
                and not habit.is_paused
                and not habit.is_deleted
            )
        )


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


def build_service(
    dummy_session,
    habit=None,
    active_habits=None,
    completed_dates=None,
    completed_today_ids=None,
) -> HabitService:
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
async def test_create_habit_saves_schedule_and_goal(dummy_session) -> None:
    service = build_service(dummy_session)

    habit = await service.create_habit(
        1,
        "Walk",
        frequency_type=HabitScheduleService.INTERVAL,
        frequency_interval=2,
        reminder_enabled=True,
        reminder_time=time(9, 30),
        start_date=date(2026, 4, 4),
        goal_type=HabitGoalService.COMPLETIONS,
        goal_target_value=20,
    )

    assert habit.frequency_type == "interval"
    assert habit.frequency_interval == 2
    assert habit.week_days_mask is None
    assert habit.reminder_enabled is True
    assert habit.reminder_time == time(9, 30)
    assert habit.goal_type == "completions"
    assert habit.goal_target_value == 20


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
async def test_get_visible_habits_keeps_paused_habit_in_main_list(dummy_session) -> None:
    active_habit = make_habit(id=1, user_id=1, title="Daily")
    paused_habit = make_habit(id=2, user_id=1, title="Read", is_paused=True)
    service = build_service(
        dummy_session,
        active_habits=[active_habit, paused_habit],
    )

    result = await service.get_visible_habits(1)

    assert [item.id for item in result] == [1, 2]
    assert result[0].is_paused is False
    assert result[1].is_paused is True


@pytest.mark.asyncio
async def test_get_today_habits_skips_paused_habit(dummy_session, monkeypatch) -> None:
    target_date = date(2026, 4, 4)
    active_habit = make_habit(id=1, user_id=1, title="Daily", start_date=date(2026, 4, 1))
    paused_habit = make_habit(
        id=2,
        user_id=1,
        title="Paused",
        start_date=date(2026, 4, 1),
        is_paused=True,
    )
    service = build_service(
        dummy_session,
        active_habits=[active_habit, paused_habit],
        completed_today_ids=[1, 2],
    )
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    result = await service.get_today_habits(1)

    assert [item.id for item in result] == [1]


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
async def test_complete_habit_rejects_when_habit_is_paused(dummy_session, monkeypatch) -> None:
    target_date = date(2026, 4, 4)
    habit = make_habit(
        id=5,
        user_id=1,
        start_date=date(2026, 4, 1),
        is_paused=True,
        paused_at=datetime(2026, 4, 4, 9, 0, tzinfo=timezone.utc),
    )
    service = build_service(dummy_session, habit=habit)
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    with pytest.raises(HabitPausedError):
        await service.complete_habit_for_today(1, 5)


@pytest.mark.asyncio
async def test_update_habit_schedule_resets_start_date_to_today(dummy_session, monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    habit = make_habit(
        id=5,
        user_id=1,
        frequency_type="daily",
        start_date=date(2026, 4, 1),
    )
    service = build_service(dummy_session, habit=habit)
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    habit_card = await service.update_habit_schedule(
        1,
        5,
        frequency_type=HabitScheduleService.INTERVAL,
        frequency_interval=2,
    )

    assert habit.frequency_type == "interval"
    assert habit.frequency_interval == 2
    assert habit.start_date == target_date
    assert habit_card.frequency_text == "через день"


@pytest.mark.asyncio
async def test_update_habit_schedule_to_weekdays_updates_mask_and_card(dummy_session, monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    weekdays_mask = HabitScheduleService.build_week_days_mask([0, 2, 4])
    habit = make_habit(
        id=5,
        user_id=1,
        frequency_type="daily",
        start_date=date(2026, 4, 1),
    )
    service = build_service(dummy_session, habit=habit)
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    habit_card = await service.update_habit_schedule(
        1,
        5,
        frequency_type=HabitScheduleService.WEEKDAYS,
        week_days_mask=weekdays_mask,
    )

    assert habit.frequency_type == "weekdays"
    assert habit.frequency_interval is None
    assert habit.week_days_mask == weekdays_mask
    assert habit.start_date == target_date
    assert habit_card.frequency_text == HabitScheduleService.format_weekdays(weekdays_mask)


@pytest.mark.asyncio
async def test_update_reminder_time_changes_state(dummy_session) -> None:
    habit = make_habit(id=5, user_id=1, reminder_enabled=False, reminder_time=None)
    service = build_service(dummy_session, habit=habit)

    result = await service.enable_reminder(1, 5, "09:30")

    assert result.enabled is True
    assert result.reminder_time == time(9, 30)
    assert habit.reminder_enabled is True
    assert habit.reminder_time == time(9, 30)


@pytest.mark.asyncio
async def test_disable_reminder_clears_saved_time(dummy_session) -> None:
    habit = make_habit(
        id=5,
        user_id=1,
        reminder_enabled=True,
        reminder_time=time(21, 15),
    )
    service = build_service(dummy_session, habit=habit)

    result = await service.disable_reminder(1, 5)

    assert result.enabled is False
    assert result.reminder_time is None
    assert habit.reminder_enabled is False
    assert habit.reminder_time is None


@pytest.mark.asyncio
async def test_update_habit_goal_returns_progress(dummy_session, monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    habit = make_habit(id=6, user_id=1)
    service = build_service(
        dummy_session,
        habit=habit,
        completed_dates={6: [date(2026, 4, 8), date(2026, 4, 9)]},
    )
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    habit_card = await service.update_habit_goal(
        1,
        6,
        goal_type=HabitGoalService.COMPLETIONS,
        goal_target_value=5,
    )

    assert habit.goal_type == "completions"
    assert habit.goal_target_value == 5
    assert habit_card.goal is not None
    assert habit_card.goal.progress_text == "2 / 5"
    assert habit_card.goal.goal_text == "5 выполнений"


@pytest.mark.asyncio
async def test_clear_habit_goal_removes_goal_from_card(dummy_session, monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    habit = make_habit(
        id=6,
        user_id=1,
        goal_type="streak",
        goal_target_value=7,
    )
    service = build_service(dummy_session, habit=habit)
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    habit_card = await service.clear_habit_goal(1, 6)

    assert habit.goal_type is None
    assert habit.goal_target_value is None
    assert habit_card.goal is None


@pytest.mark.asyncio
async def test_archive_habit_marks_inactive_and_commits(dummy_session) -> None:
    habit = make_habit(
        id=5,
        user_id=1,
        is_active=True,
        is_paused=True,
        paused_at=datetime(2026, 4, 4, 9, 0, tzinfo=timezone.utc),
    )
    service = build_service(dummy_session, habit=habit)

    result = await service.archive_habit(1, 5)

    assert result is True
    assert habit.is_active is False
    assert habit.is_paused is False
    assert habit.paused_at is None
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_pause_habit_marks_habit_paused_and_commits(dummy_session) -> None:
    habit = make_habit(id=5, user_id=1, is_active=True, is_paused=False)
    service = build_service(dummy_session, habit=habit)

    card = await service.pause_habit(1, 5)

    assert habit.is_paused is True
    assert habit.paused_at is not None
    assert card.is_paused is True
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_resume_habit_clears_pause_and_commits(dummy_session) -> None:
    habit = make_habit(
        id=5,
        user_id=1,
        is_active=True,
        is_paused=True,
        paused_at=datetime(2026, 4, 4, 9, 0, tzinfo=timezone.utc),
    )
    service = build_service(dummy_session, habit=habit)

    card = await service.resume_habit(1, 5)

    assert habit.is_paused is False
    assert habit.paused_at is None
    assert card.is_paused is False
    assert dummy_session.commit_calls == 1


@pytest.mark.asyncio
async def test_pause_habit_rejects_archived_habit(dummy_session) -> None:
    habit = make_habit(id=5, user_id=1, is_active=False)
    service = build_service(dummy_session, habit=habit)

    with pytest.raises(HabitArchivedError):
        await service.pause_habit(1, 5)


@pytest.mark.asyncio
async def test_resume_habit_rejects_archived_habit(dummy_session) -> None:
    habit = make_habit(id=5, user_id=1, is_active=False, is_paused=True)
    service = build_service(dummy_session, habit=habit)

    with pytest.raises(HabitArchivedError):
        await service.resume_habit(1, 5)


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


@pytest.mark.asyncio
async def test_paused_habit_remains_available_in_card_and_history(dummy_session, monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    habit = make_habit(
        id=9,
        user_id=1,
        title="Read",
        start_date=date(2026, 4, 1),
        is_paused=True,
        paused_at=datetime(2026, 4, 10, 8, 30, tzinfo=timezone.utc),
    )
    service = build_service(
        dummy_session,
        habit=habit,
        completed_dates={9: [date(2026, 4, 8), date(2026, 4, 9)]},
    )
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    card = await service.get_habit_card(1, 9)
    history = await service.get_habit_history(1, 9, days=7)

    assert card.is_paused is True
    assert history.habit_id == 9
    assert len(history.entries) == 7
