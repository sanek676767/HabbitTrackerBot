import logging
from datetime import date, datetime, time, timedelta

from aiogram import Bot, html

from app.bot.keyboards import get_summary_actions_keyboard
from app.core.database import async_session_factory
from app.repositories.habit_log_repository import HabitLogRepository
from app.repositories.habit_repository import HabitRepository
from app.repositories.user_repository import UserRepository
from app.services.progress_service import DailyProgressSummary, ProgressService, WeeklyProgressSummary
from app.services.reminder_service import ReminderService


logger = logging.getLogger(__name__)

DAILY_SUMMARY_TRIGGER_TIME = time(hour=21, minute=0)
WEEKLY_SUMMARY_TRIGGER_TIME = time(hour=20, minute=0)
WEEKLY_SUMMARY_WEEKDAY = 6


async def dispatch_due_summaries(
    bot: Bot,
    current_utc_datetime: datetime | None = None,
) -> dict[str, int]:
    normalized_utc_datetime = ReminderService.normalize_utc_datetime(current_utc_datetime)

    async with async_session_factory() as session:
        user_repository = UserRepository(session)
        progress_service = ProgressService(
            session=session,
            habit_repository=HabitRepository(session),
            habit_log_repository=HabitLogRepository(session),
        )
        users = await user_repository.get_users_for_summary_dispatch()

        daily_sent = 0
        weekly_sent = 0

        for user in users:
            user_local_datetime = _get_user_local_datetime(
                normalized_utc_datetime,
                user.utc_offset_minutes,
            )
            user_local_date = user_local_datetime.date()
            user_local_time = time(user_local_datetime.hour, user_local_datetime.minute)
            week_start = _get_week_start(user_local_date)

            if _should_send_daily_summary(
                user_local_time,
                user_local_date,
                user.last_daily_summary_sent_for_date,
            ):
                daily_summary = await progress_service.get_daily_progress_summary(user.id)
                if await _send_daily_summary(bot, user.telegram_id, daily_summary):
                    await user_repository.update_last_daily_summary_sent_for_date(
                        user,
                        user_local_date,
                    )
                    await session.commit()
                    daily_sent += 1

            if _should_send_weekly_summary(
                user_local_time,
                user_local_date,
                user.last_weekly_summary_sent_for_week_start,
            ):
                weekly_summary = await progress_service.get_weekly_progress_summary(user.id)
                if await _send_weekly_summary(bot, user.telegram_id, weekly_summary):
                    await user_repository.update_last_weekly_summary_sent_for_week_start(
                        user,
                        week_start,
                    )
                    await session.commit()
                    weekly_sent += 1

    return {
        "checked": len(users),
        "daily_sent": daily_sent,
        "weekly_sent": weekly_sent,
    }


async def _send_daily_summary(
    bot: Bot,
    telegram_id: int,
    summary: DailyProgressSummary,
) -> bool:
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=_build_daily_summary_text(summary),
            reply_markup=get_summary_actions_keyboard(),
        )
        return True
    except Exception:
        logger.exception("Failed to send daily summary to telegram_id=%s", telegram_id)
        return False


async def _send_weekly_summary(
    bot: Bot,
    telegram_id: int,
    summary: WeeklyProgressSummary,
) -> bool:
    try:
        await bot.send_message(
            chat_id=telegram_id,
            text=_build_weekly_summary_text(summary),
            reply_markup=get_summary_actions_keyboard(),
        )
        return True
    except Exception:
        logger.exception("Failed to send weekly summary to telegram_id=%s", telegram_id)
        return False


def _build_daily_summary_text(summary: DailyProgressSummary) -> str:
    if summary.remaining_today_count == 0:
        calm_line = "Спокойно: сегодняшний минимум уже закрыт."
    else:
        calm_line = (
            f"Спокойный темп: осталось ещё {summary.remaining_today_count}. "
            "Можно закрыть их без спешки."
        )

    return "\n".join(
        [
            "🌤 Ежедневная сводка",
            "",
            f"Выполнено сегодня: {summary.completed_today_count} из {summary.active_habits_count}",
            f"Осталось на сегодня: {summary.remaining_today_count}",
            "",
            calm_line,
        ]
    )


def _build_weekly_summary_text(summary: WeeklyProgressSummary) -> str:
    best_habit_text = (
        f"{html.quote(summary.best_habit_title)} - {summary.best_habit_completion_count} выполн."
        if summary.best_habit_title is not None and summary.best_habit_completion_count > 0
        else "Пока без явного лидера"
    )
    best_streak_text = (
        f"{html.quote(summary.best_streak_habit_title)} - {summary.best_streak_value} дн."
        if summary.best_streak_habit_title is not None and summary.best_streak_value > 0
        else "Пока без длинной серии"
    )
    problem_habits_text = (
        ", ".join(html.quote(title) for title in summary.problem_habits)
        if summary.problem_habits
        else "Провалов за неделю не видно"
    )

    return "\n".join(
        [
            "🗓 Недельная сводка",
            "",
            f"Всего выполнений за неделю: {summary.total_completions}",
            f"Средний процент выполнения: {_format_percentage(summary.average_completion_rate)}",
            f"Лучшая привычка недели: {best_habit_text}",
            f"Лучшая серия: {best_streak_text}",
            f"Нуждаются во внимании: {problem_habits_text}",
            "",
            "Неделя выглядит устойчиво. Дальше лучше просто держать ритм.",
        ]
    )


def _get_user_local_datetime(
    normalized_utc_datetime: datetime,
    utc_offset_minutes: int | None,
) -> datetime:
    if utc_offset_minutes is None:
        return normalized_utc_datetime
    return ReminderService.get_user_local_datetime(normalized_utc_datetime, utc_offset_minutes)


def _get_week_start(target_date: date) -> date:
    return target_date - timedelta(days=target_date.weekday())


def _should_send_daily_summary(
    current_local_time: time,
    current_local_date: date,
    last_sent_for_date: date | None,
) -> bool:
    return (
        current_local_time == DAILY_SUMMARY_TRIGGER_TIME
        and last_sent_for_date != current_local_date
    )


def _should_send_weekly_summary(
    current_local_time: time,
    current_local_date: date,
    last_sent_for_week_start: date | None,
) -> bool:
    week_start = _get_week_start(current_local_date)
    return (
        current_local_time == WEEKLY_SUMMARY_TRIGGER_TIME
        and current_local_date.weekday() == WEEKLY_SUMMARY_WEEKDAY
        and last_sent_for_week_start != week_start
    )


def _format_percentage(value: float) -> str:
    if value.is_integer():
        return f"{int(value)}%"
    return f"{value:.1f}%"
