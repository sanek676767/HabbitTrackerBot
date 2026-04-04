import asyncio
import logging
from datetime import datetime, timezone

from aiogram import Bot

from app.bot.reminder_dispatcher import dispatch_due_reminders
from app.bot.summary_dispatcher import dispatch_due_summaries
from app.services.reminder_service import ReminderService


logger = logging.getLogger(__name__)


async def run_inline_reminder_loop(
    bot: Bot,
    stop_event: asyncio.Event,
    *,
    poll_interval_seconds: int = 5,
) -> None:
    logger.info("Starting inline reminder and summary loop")
    last_checked_minute = None

    while not stop_event.is_set():
        current_utc_minute = ReminderService.normalize_utc_datetime(datetime.now(timezone.utc))

        if current_utc_minute != last_checked_minute:
            try:
                reminder_result = await dispatch_due_reminders(bot, current_utc_minute)
                summary_result = await dispatch_due_summaries(bot, current_utc_minute)

                if reminder_result["checked"] or reminder_result["sent"]:
                    logger.info(
                        "Inline reminder dispatch completed: checked=%s sent=%s",
                        reminder_result["checked"],
                        reminder_result["sent"],
                    )
                if summary_result["checked"] or summary_result["daily_sent"] or summary_result["weekly_sent"]:
                    logger.info(
                        "Inline summary dispatch completed: checked=%s daily_sent=%s weekly_sent=%s",
                        summary_result["checked"],
                        summary_result["daily_sent"],
                        summary_result["weekly_sent"],
                    )
            except Exception:
                logger.exception("Inline reminder or summary dispatch failed")
            finally:
                last_checked_minute = current_utc_minute

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval_seconds)
        except asyncio.TimeoutError:
            continue

    logger.info("Inline reminder and summary loop stopped")
