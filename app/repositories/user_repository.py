from datetime import date

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        statement = select(User).where(User.telegram_id == telegram_id)
        return await self._session.scalar(statement)

    async def create(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        self._session.add(user)
        await self._session.flush()
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id)
        return await self._session.scalar(statement)

    async def get_users_for_summary_dispatch(self) -> list[User]:
        active_habits_exists = exists(
            select(Habit.id).where(
                Habit.user_id == User.id,
                Habit.is_active.is_(True),
                Habit.is_deleted.is_(False),
            )
        )
        statement = (
            select(User)
            .where(
                User.is_blocked.is_(False),
                active_habits_exists,
            )
            .order_by(User.id.asc())
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def update_utc_offset_minutes(self, user: User, utc_offset_minutes: int) -> User:
        user.utc_offset_minutes = utc_offset_minutes
        await self._session.flush()
        return user

    async def update_last_daily_summary_sent_for_date(
        self,
        user: User,
        summary_date: date,
    ) -> User:
        user.last_daily_summary_sent_for_date = summary_date
        await self._session.flush()
        return user

    async def update_last_weekly_summary_sent_for_week_start(
        self,
        user: User,
        week_start: date,
    ) -> User:
        user.last_weekly_summary_sent_for_week_start = week_start
        await self._session.flush()
        return user
