from datetime import date, datetime, timezone

from app.services.habit_goal_service import HabitGoalService
from app.services.habit_schedule_service import HabitScheduleService
from tests.helpers import make_habit


def test_goal_by_completions_counts_total_completions() -> None:
    habit = make_habit(
        goal_type="completions",
        goal_target_value=10,
        start_date=date(2026, 4, 1),
    )
    completion_dates = [
        date(2026, 4, 1),
        date(2026, 4, 3),
        date(2026, 4, 4),
    ]

    progress = HabitGoalService.calculate_progress(
        habit,
        completion_dates,
        date(2026, 4, 4),
    )

    assert progress is not None
    assert progress.goal_text == "10 выполнений"
    assert progress.progress_text == "3 / 10"
    assert progress.is_achieved is False


def test_goal_by_completions_ignores_future_completion_dates() -> None:
    habit = make_habit(
        goal_type="completions",
        goal_target_value=5,
        start_date=date(2026, 4, 1),
    )
    completion_dates = {
        date(2026, 4, 1),
        date(2026, 4, 2),
        date(2026, 4, 10),
    }

    progress = HabitGoalService.calculate_progress(
        habit,
        completion_dates,
        date(2026, 4, 2),
    )

    assert progress is not None
    assert progress.current_value == 2
    assert progress.progress_text == "2 / 5"
    assert progress.is_achieved is False


def test_goal_by_streak_uses_schedule_aware_current_streak() -> None:
    habit = make_habit(
        frequency_type="interval",
        frequency_interval=2,
        start_date=date(2026, 4, 1),
        goal_type="streak",
        goal_target_value=4,
    )
    completion_dates = {
        date(2026, 4, 1),
        date(2026, 4, 3),
        date(2026, 4, 5),
    }

    progress = HabitGoalService.calculate_progress(
        habit,
        completion_dates,
        date(2026, 4, 5),
    )

    assert progress is not None
    assert progress.goal_text == "серия 4 дня"
    assert progress.progress_text == "3 / 4"
    assert progress.is_achieved is False


def test_goal_by_streak_respects_weekday_schedule() -> None:
    mask = HabitScheduleService.build_week_days_mask([0, 2, 4])
    habit = make_habit(
        frequency_type="weekdays",
        week_days_mask=mask,
        start_date=date(2026, 3, 30),
        goal_type="streak",
        goal_target_value=3,
    )
    completion_dates = {
        date(2026, 3, 30),
        date(2026, 4, 1),
        date(2026, 4, 3),
    }

    progress = HabitGoalService.calculate_progress(
        habit,
        completion_dates,
        date(2026, 4, 3),
    )

    assert progress is not None
    assert progress.progress_text == "3 / 3"
    assert progress.is_achieved is True


def test_resolve_goal_achieved_at_sets_timestamp_once() -> None:
    habit = make_habit(
        goal_type="completions",
        goal_target_value=2,
        goal_achieved_at=None,
    )
    progress = HabitGoalService.calculate_progress(
        habit,
        [date(2026, 4, 1), date(2026, 4, 2)],
        date(2026, 4, 2),
    )
    now = datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc)

    achieved_at = HabitGoalService.resolve_goal_achieved_at(habit, progress, now=now)

    assert achieved_at == now
