"""Промежуточный слой, который отмечает последнее взаимодействие пользователя с ботом."""

from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.database import async_session_factory
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


class UserActivityMiddleware(BaseMiddleware):
    def __init__(
        self,
        activity_toucher: Callable[[int], Awaitable[None]] | None = None,
    ) -> None:
        self._activity_toucher = activity_toucher or self._touch_activity

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_id = self._extract_telegram_id(event)
        if telegram_id is not None:
            await self._activity_toucher(telegram_id)
        return await handler(event, data)

    @staticmethod
    def _extract_telegram_id(event: TelegramObject) -> int | None:
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            return None
        return getattr(from_user, "id", None)

    @staticmethod
    async def _touch_activity(telegram_id: int) -> None:
        async with async_session_factory() as session:
            user_service = UserService(
                session=session,
                user_repository=UserRepository(session),
            )
            await user_service.touch_last_interaction(telegram_id)
