from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.core.database import async_session_factory
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.habit_log_repository import HabitLogRepository
from app.repositories.habit_repository import HabitRepository
from app.repositories.user_repository import UserRepository
from app.services.admin_service import AdminService
from app.services.feedback_service import FeedbackService
from app.services.habit_service import HabitService
from app.services.progress_service import ProgressService
from app.services.user_service import UserService


class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with async_session_factory() as session:
            user_repository = UserRepository(session)
            habit_repository = HabitRepository(session)
            habit_log_repository = HabitLogRepository(session)
            feedback_repository = FeedbackRepository(session)

            data["session"] = session
            data["habit_service"] = HabitService(
                session=session,
                habit_repository=habit_repository,
                habit_log_repository=habit_log_repository,
            )
            data["progress_service"] = ProgressService(
                session=session,
                habit_repository=habit_repository,
                habit_log_repository=habit_log_repository,
            )
            data["user_service"] = UserService(
                session=session,
                user_repository=user_repository,
            )
            data["admin_service"] = AdminService(
                session=session,
                user_repository=user_repository,
                habit_repository=habit_repository,
                feedback_repository=feedback_repository,
            )
            data["feedback_service"] = FeedbackService(
                session=session,
                user_repository=user_repository,
                feedback_repository=feedback_repository,
            )

            try:
                return await handler(event, data)
            except Exception:
                await session.rollback()
                raise
