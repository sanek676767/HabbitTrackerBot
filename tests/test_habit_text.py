from datetime import datetime, time, timezone

from app.bot.habit_text import (
    build_habit_card_text,
    build_habit_edit_menu_text,
    build_habit_stats_text,
)
from app.services.habit_goal_service import HabitGoalProgress
from app.services.habit_service import HabitCard, HabitStats, HabitStatsWindow


def _make_goal() -> HabitGoalProgress:
    return HabitGoalProgress(
        goal_type="completions",
        target_value=20,
        current_value=8,
        goal_text="20 выполнений",
        progress_text="8 / 20",
        is_achieved=False,
        status_text=None,
        achieved_at=None,
    )


def test_build_habit_edit_menu_text_shows_goal_progress() -> None:
    habit_card = HabitCard(
        id=1,
        title="Читать",
        is_completed_today=False,
        is_due_today=True,
        total_completions=8,
        current_streak=5,
        best_streak=7,
        is_active=True,
        reminder_enabled=True,
        reminder_time=time(9, 30),
        frequency_text="ежедневно",
        goal=_make_goal(),
    )

    text = build_habit_edit_menu_text(habit_card)

    assert "Напоминание: 09:30" in text
    assert "Статус: активна" in text
    assert "Цель: 20 выполнений" in text
    assert "Прогресс цели: 8 / 20" in text
    assert "Выбери, что хочешь изменить." in text


def test_build_habit_card_text_shows_pause_explanation() -> None:
    habit_card = HabitCard(
        id=1,
        title="Читать",
        is_completed_today=False,
        is_due_today=False,
        total_completions=8,
        current_streak=5,
        best_streak=7,
        is_active=True,
        reminder_enabled=True,
        reminder_time=time(9, 30),
        frequency_text="ежедневно",
        goal=_make_goal(),
        is_paused=True,
    )

    text = build_habit_card_text(habit_card)

    assert "Сегодня: временно приостановлена" in text
    assert "Статус: на паузе" in text
    assert (
        "Пока привычка на паузе, она не участвует в ежедневном списке и напоминаниях."
        in text
    )


def test_build_habit_stats_text_shows_compact_windows_and_goal_remaining() -> None:
    stats = HabitStats(
        id=1,
        title="Читать",
        total_completions=8,
        is_completed_today=False,
        is_due_today=True,
        current_streak=5,
        best_streak=7,
        last_7_days_progress_text="04.04: ✅",
        created_at=datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc),
        frequency_text="ежедневно",
        goal=_make_goal(),
        goal_remaining_text="осталось 12 выполнений",
        windows=[
            HabitStatsWindow(days=7, completion_rate_percent=57, planned_days=7, completed_days=4),
            HabitStatsWindow(days=14, completion_rate_percent=40, planned_days=10, completed_days=4),
            HabitStatsWindow(days=30, completion_rate_percent=26, planned_days=30, completed_days=8),
        ],
        is_active=True,
        is_paused=False,
    )

    text = build_habit_stats_text(stats)

    assert "Цель: 20 выполнений" in text
    assert "Прогресс: 8 / 20" in text
    assert "До цели: осталось 12 выполнений" in text
    assert "• 7 дн.: 57% — 4 из 7" in text
    assert "• 14 дн.: 40% — 4 из 10" in text
    assert "• 30 дн.: 26% — 8 из 30" in text
    assert "Последние 7 дней:" not in text
