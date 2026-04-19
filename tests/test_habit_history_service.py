from datetime import date, timedelta

import pytest

from app.services.habit_schedule_service import HabitScheduleService
from app.services.habit_service import HabitDeletedError, HabitService
from tests.helpers import DummySession, make_habit


class FakeHabitRepository:
    def __init__(self, habit=None) -> None:
        self.habit = habit

    async def get_habit_by_id_for_user(self, habit_id: int, user_id: int):
        if self.habit is None:
            return None
        if self.habit.id != habit_id or self.habit.user_id != user_id:
            return None
        return self.habit


class FakeHabitLogRepository:
    def __init__(self, completed_dates=None) -> None:
        self.completed_dates = completed_dates or {}

    async def get_completion_dates(self, habit_id: int) -> list[date]:
        return sorted(self.completed_dates.get(habit_id, []))


def build_service(*, habit=None, completed_dates=None) -> HabitService:
    return HabitService(
        session=DummySession(),
        habit_repository=FakeHabitRepository(habit),
        habit_log_repository=FakeHabitLogRepository(completed_dates),
    )


@pytest.mark.asyncio
async def test_habit_history_for_daily_habit_marks_all_statuses(monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    habit = make_habit(
        id=1,
        user_id=1,
        title="Вода",
        frequency_type=HabitScheduleService.DAILY,
        start_date=date(2026, 4, 7),
    )
    service = build_service(
        habit=habit,
        completed_dates={1: [date(2026, 4, 7)]},
    )
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    history = await service.get_habit_history(1, 1, days=7)

    assert history.period_days == 7
    assert [(entry.day, entry.status) for entry in history.entries] == [
        (date(2026, 4, 4), "не запланировано"),
        (date(2026, 4, 5), "не запланировано"),
        (date(2026, 4, 6), "не запланировано"),
        (date(2026, 4, 7), "выполнено"),
        (date(2026, 4, 8), "пропущено"),
        (date(2026, 4, 9), "пропущено"),
        (date(2026, 4, 10), "ждёт отметку"),
    ]


@pytest.mark.asyncio
async def test_habit_history_for_interval_habit_respects_due_logic(monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    habit = make_habit(
        id=2,
        user_id=1,
        title="Тренировка",
        frequency_type=HabitScheduleService.INTERVAL,
        frequency_interval=2,
        start_date=date(2026, 4, 4),
    )
    service = build_service(
        habit=habit,
        completed_dates={2: [date(2026, 4, 4), date(2026, 4, 8)]},
    )
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    history = await service.get_habit_history(1, 2, days=7)

    assert [entry.status for entry in history.entries] == [
        "выполнено",
        "не запланировано",
        "пропущено",
        "не запланировано",
        "выполнено",
        "не запланировано",
        "ждёт отметку",
    ]


@pytest.mark.asyncio
async def test_habit_history_for_weekdays_habit_respects_due_logic(monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    week_days_mask = HabitScheduleService.build_week_days_mask([0, 2, 4])
    habit = make_habit(
        id=3,
        user_id=1,
        title="Испанский",
        frequency_type=HabitScheduleService.WEEKDAYS,
        week_days_mask=week_days_mask,
        start_date=date(2026, 4, 1),
    )
    service = build_service(
        habit=habit,
        completed_dates={3: [date(2026, 4, 6)]},
    )
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    history = await service.get_habit_history(1, 3, days=7)

    assert [entry.status for entry in history.entries] == [
        "не запланировано",
        "не запланировано",
        "выполнено",
        "не запланировано",
        "пропущено",
        "не запланировано",
        "ждёт отметку",
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("days", [7, 14, 30])
async def test_habit_history_supports_all_period_buttons(days: int, monkeypatch) -> None:
    target_date = date(2026, 4, 19)
    habit = make_habit(
        id=4,
        user_id=1,
        title="Шаги",
        frequency_type=HabitScheduleService.DAILY,
        start_date=date(2026, 3, 1),
    )
    service = build_service(habit=habit)
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    history = await service.get_habit_history(1, 4, days=days)

    assert history.period_days == days
    assert len(history.entries) == days
    assert history.entries[0].day == target_date - timedelta(days=days - 1)
    assert history.entries[-1].day == target_date


@pytest.mark.asyncio
async def test_habit_history_is_available_for_archived_habit(monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    habit = make_habit(
        id=5,
        user_id=1,
        title="Книга",
        is_active=False,
        is_deleted=False,
        start_date=date(2026, 4, 1),
    )
    service = build_service(habit=habit)
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    history = await service.get_habit_history(1, 5, days=7)

    assert history.title == "Книга"
    assert history.entries[-1].status == "ждёт отметку"


@pytest.mark.asyncio
async def test_habit_history_is_unavailable_for_deleted_habit(monkeypatch) -> None:
    target_date = date(2026, 4, 10)
    habit = make_habit(
        id=6,
        user_id=1,
        is_deleted=True,
        is_active=False,
    )
    service = build_service(habit=habit)
    monkeypatch.setattr(HabitService, "_get_today", staticmethod(lambda: target_date))

    with pytest.raises(HabitDeletedError):
        await service.get_habit_history(1, 6, days=7)
