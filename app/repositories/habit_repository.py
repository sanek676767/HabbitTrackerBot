from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit


class HabitRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_habit(
        self,
        user_id: int,
        title: str,
        frequency_type: str = "daily",
    ) -> Habit:
        habit = Habit(
            user_id=user_id,
            title=title,
            frequency_type=frequency_type,
        )
        self._session.add(habit)
        await self._session.flush()
        return habit

    async def get_active_habits_by_user(self, user_id: int) -> list[Habit]:
        statement = (
            select(Habit)
            .where(Habit.user_id == user_id, Habit.is_active.is_(True))
            .order_by(Habit.created_at.asc(), Habit.id.asc())
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def get_archived_habits_by_user(self, user_id: int) -> list[Habit]:
        statement = (
            select(Habit)
            .where(Habit.user_id == user_id, Habit.is_active.is_(False))
            .order_by(Habit.updated_at.desc(), Habit.id.desc())
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def get_habit_by_id(self, habit_id: int) -> Habit | None:
        statement = select(Habit).where(Habit.id == habit_id)
        return await self._session.scalar(statement)

    async def get_habit_by_id_for_user(self, habit_id: int, user_id: int) -> Habit | None:
        statement = select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
        return await self._session.scalar(statement)

    async def archive_habit(self, habit: Habit) -> Habit:
        habit.is_active = False
        await self._session.flush()
        return habit

    async def restore_habit(self, habit: Habit) -> Habit:
        habit.is_active = True
        await self._session.flush()
        return habit

    async def count_active_habits(self, user_id: int) -> int:
        statement = select(func.count(Habit.id)).where(
            Habit.user_id == user_id,
            Habit.is_active.is_(True),
        )
        result = await self._session.scalar(statement)
        return int(result or 0)
