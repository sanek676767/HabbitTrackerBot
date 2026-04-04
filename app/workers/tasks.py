import asyncio
from datetime import datetime, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.bot.reminder_dispatcher import dispatch_due_reminders
from app.core.config import settings
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.debug_ping")
def debug_ping() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@celery_app.task(name="app.workers.tasks.dispatch_habit_reminders")
def dispatch_habit_reminders() -> dict[str, int]:
    return asyncio.run(_dispatch_habit_reminders())


async def _dispatch_habit_reminders() -> dict[str, int]:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        return await dispatch_due_reminders(bot, datetime.now(timezone.utc))
    finally:
        await bot.session.close()
