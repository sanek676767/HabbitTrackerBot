from aiogram import html

from app.services.habit_service import HabitCard, HabitHistory, HabitStats


def build_habit_card_text(habit_card: HabitCard) -> str:
    if habit_card.is_completed_today:
        today_status = "выполнена"
    elif habit_card.is_due_today:
        today_status = "ждёт отметку"
    else:
        today_status = "на сегодня не запланирована"

    reminder_status = (
        habit_card.reminder_time.strftime("%H:%M")
        if habit_card.reminder_enabled and habit_card.reminder_time is not None
        else "без напоминания"
    )
    active_status = "активна" if habit_card.is_active else "в архиве"

    lines = [
        f"📌 {html.quote(habit_card.title)}",
        "",
        f"Частота: {habit_card.frequency_text}",
        f"Сегодня: {today_status}",
        f"Текущая серия: {habit_card.current_streak}",
        f"Лучшая серия: {habit_card.best_streak}",
        f"Всего отметок: {habit_card.total_completions}",
        f"Напоминание: {reminder_status}",
        f"Статус: {active_status}",
    ]

    if habit_card.goal is None:
        lines.append("Цель: без цели")
    else:
        lines.append(f"Цель: {habit_card.goal.goal_text}")
        lines.append(f"Прогресс: {habit_card.goal.progress_text}")
        if habit_card.goal.status_text is not None:
            lines.append(f"Результат: {habit_card.goal.status_text}")

    return "\n".join(lines)


def build_habit_edit_menu_text(habit_card: HabitCard) -> str:
    reminder_text = (
        habit_card.reminder_time.strftime("%H:%M")
        if habit_card.reminder_enabled and habit_card.reminder_time is not None
        else "без напоминания"
    )

    lines = [
        f"✏️ Редактирование «{html.quote(habit_card.title)}»",
        "",
        f"Частота: {habit_card.frequency_text}",
        f"Напоминание: {reminder_text}",
    ]

    if habit_card.goal is None:
        lines.append("Цель: без цели")
    else:
        lines.append(f"Цель: {habit_card.goal.goal_text}")
        lines.append(f"Прогресс цели: {habit_card.goal.progress_text}")
        if habit_card.goal.status_text is not None:
            lines.append(f"Результат: {habit_card.goal.status_text}")

    lines.extend(
        [
            "",
            "Выбери, что хочешь изменить.",
        ]
    )
    return "\n".join(lines)


def build_habit_stats_text(stats: HabitStats) -> str:
    today_due_text = "да" if stats.is_due_today else "нет"
    today_done_text = "да" if stats.is_completed_today else "нет"
    created_at = stats.created_at.strftime("%d.%m.%Y %H:%M")

    lines = [
        f"📊 {html.quote(stats.title)}",
        "",
        f"Частота: {stats.frequency_text}",
        f"Есть в плане на сегодня: {today_due_text}",
        f"Отмечена сегодня: {today_done_text}",
        f"Текущая серия: {stats.current_streak}",
        f"Лучшая серия: {stats.best_streak}",
        f"Всего отметок: {stats.total_completions}",
    ]

    if stats.goal is None:
        lines.append("Цель: не задана")
    else:
        lines.append(f"Цель: {stats.goal.goal_text}")
        lines.append(f"Прогресс: {stats.goal.progress_text}")
        lines.append(
            "Результат: цель достигнута" if stats.goal.is_achieved else "Результат: цель ещё в работе"
        )

    lines.extend(
        [
            "",
            "Последние 7 дней:",
            stats.last_7_days_progress_text,
            "",
            f"Создана: {created_at}",
        ]
    )
    return "\n".join(lines)


def build_habit_history_text(history: HabitHistory) -> str:
    lines = [
        f"🗓 {html.quote(history.title)}",
        "",
        f"Частота: {history.frequency_text}",
    ]

    if history.goal_text is not None:
        lines.append(f"Цель: {history.goal_text}")

    lines.extend(
        [
            f"Период: {history.period_days} {_format_days_label(history.period_days)}",
            "",
        ]
    )
    lines.extend(
        f"{entry.day.strftime('%d.%m')} — {entry.status}"
        for entry in history.entries
    )
    return "\n".join(lines)


def build_delete_confirm_text(habit_card: HabitCard) -> str:
    return "\n".join(
        [
            f"🗑 Удалить привычку «{html.quote(habit_card.title)}»?",
            "",
            "Она исчезнет из твоих списков. Если понадобится, её сможет вернуть администратор.",
        ]
    )


def _format_days_label(days: int) -> str:
    if 11 <= days % 100 <= 14:
        return "дней"
    if days % 10 == 1:
        return "день"
    if 2 <= days % 10 <= 4:
        return "дня"
    return "дней"
