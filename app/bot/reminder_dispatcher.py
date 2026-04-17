"""Слой отправки уведомлений-напоминаний."""

import logging
from datetime import datetime, timezone

from aiogram import Bot, html

from app.bot.keyboards import get_habit_reminder_notification_keyboard
from app.core.database import async_session_factory
from app.repositories.habit_log_repository import HabitLogRepository
from app.repositories.habit_repository import HabitRepository
from app.services.reminder_service import ReminderService


logger = logging.getLogger(__name__)


async def dispatch_due_reminders(
    bot: Bot,
    current_utc_datetime: datetime | None = None,
) -> dict[str, int]:
    """Находит актуальные напоминания и отправляет их по одному через Telegram."""

    normalized_utc_datetime = ReminderService.normalize_utc_datetime(
        current_utc_datetime or datetime.now(timezone.utc)
    )

    async with async_session_factory() as session:
        reminder_service = ReminderService(
            habit_repository=HabitRepository(session),
            habit_log_repository=HabitLogRepository(session),
        )
        due_reminders = await reminder_service.get_due_habit_reminders(normalized_utc_datetime)

    if not due_reminders:
        return {"checked": 0, "sent": 0}

    sent_count = 0
    for reminder in due_reminders:
        try:
            await bot.send_message(
                chat_id=reminder.telegram_id,
                text=(
                    "Напоминание: пора вернуться к привычке "
                    f"«{html.quote(reminder.habit_title)}»."
                ),
                reply_markup=get_habit_reminder_notification_keyboard(reminder.habit_id),
            )
            sent_count += 1
        except Exception:
            # Сбой при отправке одного сообщения не должен останавливать
            # доставку остальных напоминаний из той же пачки.
            logger.exception(
                "Failed to send reminder for habit_id=%s telegram_id=%s",
                reminder.habit_id,
                reminder.telegram_id,
            )

    return {"checked": len(due_reminders), "sent": sent_count}
