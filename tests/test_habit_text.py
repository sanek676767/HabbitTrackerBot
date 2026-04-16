from datetime import time

from app.bot.habit_text import build_habit_edit_menu_text
from app.services.habit_goal_service import HabitGoalProgress
from app.services.habit_service import HabitCard


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
        goal=HabitGoalProgress(
            goal_type="completions",
            target_value=20,
            current_value=8,
            goal_text="20 выполнений",
            progress_text="8 / 20",
            is_achieved=False,
            status_text=None,
            achieved_at=None,
        ),
    )

    text = build_habit_edit_menu_text(habit_card)

    assert "Напоминание: 09:30" in text
    assert "Цель: 20 выполнений" in text
    assert "Прогресс цели: 8 / 20" in text
    assert "Выбери, что хочешь изменить." in text
