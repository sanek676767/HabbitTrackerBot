from datetime import date

from app.bot.habit_text import build_habit_history_text
from app.services.habit_service import HabitHistory, HabitHistoryDay


def test_build_habit_history_text_shows_goal_period_and_statuses() -> None:
    history = HabitHistory(
        habit_id=1,
        title="Читать",
        frequency_text="через день",
        goal_text="20 выполнений",
        period_days=14,
        entries=[
            HabitHistoryDay(day=date(2026, 4, 10), status="выполнено"),
            HabitHistoryDay(day=date(2026, 4, 11), status="не запланировано"),
            HabitHistoryDay(day=date(2026, 4, 12), status="пропущено"),
            HabitHistoryDay(day=date(2026, 4, 13), status="ждёт отметку"),
        ],
    )

    text = build_habit_history_text(history)

    assert "🗓 Читать" in text
    assert "Частота: через день" in text
    assert "Цель: 20 выполнений" in text
    assert "Период: 14 дней" in text
    assert "10.04 — выполнено" in text
    assert "11.04 — не запланировано" in text
    assert "12.04 — пропущено" in text
    assert "13.04 — ждёт отметку" in text
