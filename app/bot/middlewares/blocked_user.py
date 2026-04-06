from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.core.database import async_session_factory
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


BLOCKED_USER_TEXT = "Доступ к боту временно ограничен. Обратись к администратору."


class BlockedUserMiddleware(BaseMiddleware):
    def __init__(
        self,
        user_loader: Callable[[int], Awaitable[Any | None]] | None = None,
    ) -> None:
        self._user_loader = user_loader or self._load_user

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        telegram_id = self._extract_telegram_id(event)
        if telegram_id is None:
            return await handler(event, data)

        user = await self._user_loader(telegram_id)
        if UserService.can_use_bot(user):
            return await handler(event, data)

        if isinstance(event, Message):
            await event.answer(BLOCKED_USER_TEXT)
            return None

        if isinstance(event, CallbackQuery):
            await event.answer(BLOCKED_USER_TEXT, show_alert=True)
            return None

        return None

    @staticmethod
    def _extract_telegram_id(event: TelegramObject) -> int | None:
        from_user = getattr(event, "from_user", None)
        if from_user is None:
            return None
        return getattr(from_user, "id", None)

    @staticmethod
    async def _load_user(telegram_id: int):
        async with async_session_factory() as session:
            user_service = UserService(
                session=session,
                user_repository=UserRepository(session),
            )
            return await user_service.get_by_telegram_id(telegram_id)
