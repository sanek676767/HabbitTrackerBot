import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.bot.handlers import routers
from app.bot.middlewares.blocked_user import BlockedUserMiddleware
from app.bot.middlewares.db_session import DbSessionMiddleware
from app.bot.reminder_runner import run_inline_reminder_loop
from app.core.config import settings
from app.core.database import check_database_connection, dispose_engine
from app.core.logging import configure_logging
from app.core.redis import close_redis, get_redis


logger = logging.getLogger(__name__)


async def main() -> None:
    configure_logging()

    await check_database_connection()
    if settings.redis_enabled:
        await get_redis().ping()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Открыть бота"),
            BotCommand(command="admin", description="Открыть админку"),
            BotCommand(command="help", description="Показать помощь"),
            BotCommand(command="profile", description="Показать профиль"),
            BotCommand(command="feedback", description="Отправить обратную связь"),
        ]
    )
    dispatcher = Dispatcher()
    dispatcher.message.middleware(DbSessionMiddleware())
    dispatcher.callback_query.middleware(DbSessionMiddleware())
    dispatcher.message.middleware(BlockedUserMiddleware())
    dispatcher.callback_query.middleware(BlockedUserMiddleware())

    for router in routers:
        dispatcher.include_router(router)

    reminder_stop_event = asyncio.Event()
    reminder_task = None
    if not settings.redis_enabled:
        reminder_task = asyncio.create_task(
            run_inline_reminder_loop(bot, reminder_stop_event)
        )
        logger.info("Inline reminder runtime enabled because REDIS_ENABLED=false")

    logger.info("Starting Telegram bot polling")

    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        if reminder_task is not None:
            reminder_stop_event.set()
            with suppress(asyncio.CancelledError):
                await reminder_task
        await bot.session.close()
        if settings.redis_enabled:
            await close_redis()
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
