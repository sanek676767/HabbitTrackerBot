"""Хелперы доступа к данным пользователей."""

from datetime import date

from sqlalchemy import String, cast, exists, func, or_, select
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

    async def get_admin_users(self) -> list[User]:
        statement = (
            select(User)
            .where(
                User.is_admin.is_(True),
                User.is_blocked.is_(False),
            )
            .order_by(User.id.asc())
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def count_users(self) -> int:
        statement = select(func.count(User.id))
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def count_admin_users(self) -> int:
        statement = select(func.count(User.id)).where(User.is_admin.is_(True))
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def count_blocked_users(self) -> int:
        statement = select(func.count(User.id)).where(User.is_blocked.is_(True))
        result = await self._session.scalar(statement)
        return int(result or 0)

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
                # Пропускаем заблокированных пользователей и тех, у кого нет
                # активных привычек, чтобы периодический обход был дешевле.
                User.is_blocked.is_(False),
                active_habits_exists,
            )
            .order_by(User.id.asc())
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def search_users(
        self,
        query: str,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[User]:
        statement = self._apply_search_filter(
            select(User),
            query,
        ).order_by(User.id.asc())
        statement = statement.limit(limit).offset(offset)
        result = await self._session.scalars(statement)
        return list(result)

    async def count_search_users(self, query: str) -> int:
        statement = self._apply_search_filter(
            select(func.count(User.id)),
            query,
        )
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def update_is_blocked(self, user: User, is_blocked: bool) -> User:
        user.is_blocked = is_blocked
        await self._session.flush()
        return user

    async def update_is_admin(self, user: User, is_admin: bool) -> User:
        user.is_admin = is_admin
        await self._session.flush()
        return user

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

    @staticmethod
    def _apply_search_filter(statement, query: str):
        normalized_query = query.strip()
        if not normalized_query:
            return statement

        like_query = f"%{normalized_query}%"
        return statement.where(
            or_(
                cast(User.telegram_id, String).ilike(like_query),
                User.username.ilike(like_query),
                User.first_name.ilike(like_query),
                User.last_name.ilike(like_query),
            )
        )
