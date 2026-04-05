from datetime import date

from app.services.habit_schedule_service import HabitScheduleService
from tests.helpers import make_habit


def test_daily_schedule_is_due_every_day() -> None:
    habit = make_habit(start_date=date(2026, 4, 1))

    assert HabitScheduleService.is_habit_due_on_date(habit, date(2026, 4, 4)) is True
    assert HabitScheduleService.is_habit_due_on_date(habit, date(2026, 4, 5)) is True


def test_every_other_day_schedule_respects_start_date() -> None:
    habit = make_habit(
        frequency_type="interval",
        frequency_interval=2,
        start_date=date(2026, 4, 1),
    )

    assert HabitScheduleService.is_habit_due_on_date(habit, date(2026, 4, 1)) is True
    assert HabitScheduleService.is_habit_due_on_date(habit, date(2026, 4, 2)) is False
    assert HabitScheduleService.is_habit_due_on_date(habit, date(2026, 4, 3)) is True


def test_weekdays_schedule_checks_mask() -> None:
    mask = HabitScheduleService.build_week_days_mask([0, 2, 4])
    habit = make_habit(
        frequency_type="weekdays",
        week_days_mask=mask,
        start_date=date(2026, 4, 1),
    )

    assert HabitScheduleService.is_habit_due_on_date(habit, date(2026, 4, 3)) is True
    assert HabitScheduleService.is_habit_due_on_date(habit, date(2026, 4, 4)) is False


def test_current_streak_uses_scheduled_occurrences_for_interval_habit() -> None:
    habit = make_habit(
        frequency_type="interval",
        frequency_interval=2,
        start_date=date(2026, 4, 1),
    )
    completion_dates = {
        date(2026, 4, 1),
        date(2026, 4, 3),
        date(2026, 4, 5),
    }

    result = HabitScheduleService.calculate_current_streak(
        habit,
        completion_dates,
        date(2026, 4, 5),
    )

    assert result == 3


def test_best_streak_uses_scheduled_occurrences_for_weekdays_habit() -> None:
    mask = HabitScheduleService.build_week_days_mask([0, 2, 4])
    habit = make_habit(
        frequency_type="weekdays",
        week_days_mask=mask,
        start_date=date(2026, 3, 30),
    )
    completion_dates = {
        date(2026, 3, 30),
        date(2026, 4, 1),
        date(2026, 4, 4),
        date(2026, 4, 6),
    }

    result = HabitScheduleService.calculate_best_streak(
        habit,
        completion_dates,
        date(2026, 4, 6),
    )

    assert result == 2
