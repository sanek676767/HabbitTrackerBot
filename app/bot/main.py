import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from app.bot.handlers import routers
from app.bot.middlewares.db_session import DbSessionMiddleware
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
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="profile", description="Показать профиль"),
        ]
    )
    dispatcher = Dispatcher()
    dispatcher.message.middleware(DbSessionMiddleware())

    for router in routers:
        dispatcher.include_router(router)

    logger.info("Starting Telegram bot polling")

    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()
        if settings.redis_enabled:
            await close_redis()
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
