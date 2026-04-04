from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, session: AsyncSession, user_repository: UserRepository) -> None:
        self._session = session
        self._user_repository = user_repository

    async def get_or_create_user(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> tuple[User, bool]:
        user = await self._user_repository.get_by_telegram_id(telegram_id)

        if user is None:
            user = await self._user_repository.create(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            await self._session.commit()
            await self._session.refresh(user)
            return user, True

        is_updated = False
        if user.username != username:
            user.username = username
            is_updated = True
        if user.first_name != first_name:
            user.first_name = first_name
            is_updated = True
        if user.last_name != last_name:
            user.last_name = last_name
            is_updated = True

        if is_updated:
            await self._session.commit()
            await self._session.refresh(user)

        return user, False

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self._user_repository.get_by_telegram_id(telegram_id)
