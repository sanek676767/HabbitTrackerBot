from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.database import async_session_factory
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            data["session"] = session
            data["user_service"] = UserService(
                session=session,
                user_repository=UserRepository(session),
            )

            try:
                return await handler(event, data)
            except Exception:
                await session.rollback()
                raise
