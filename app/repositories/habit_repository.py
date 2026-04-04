from datetime import datetime, time, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.habit import Habit
from app.models.user import User


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
            .where(
                Habit.user_id == user_id,
                Habit.is_active.is_(True),
                Habit.is_deleted.is_(False),
            )
            .order_by(Habit.created_at.asc(), Habit.id.asc())
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def get_archived_habits_by_user(self, user_id: int) -> list[Habit]:
        statement = (
            select(Habit)
            .where(
                Habit.user_id == user_id,
                Habit.is_active.is_(False),
                Habit.is_deleted.is_(False),
            )
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

    async def update_title(self, habit: Habit, title: str) -> Habit:
        habit.title = title
        await self._session.flush()
        return habit

    async def update_reminder(
        self,
        habit: Habit,
        enabled: bool,
        reminder_time: time | None,
    ) -> Habit:
        habit.reminder_enabled = enabled
        habit.reminder_time = reminder_time if enabled else None
        await self._session.flush()
        return habit

    async def get_habits_for_reminder_check(self) -> list[Habit]:
        statement = (
            select(Habit)
            .options(selectinload(Habit.user))
            .join(Habit.user)
            .where(
                Habit.is_active.is_(True),
                Habit.is_deleted.is_(False),
                Habit.reminder_enabled.is_(True),
                User.is_blocked.is_(False),
                User.utc_offset_minutes.is_not(None),
            )
            .order_by(Habit.id.asc())
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def soft_delete_habit(self, habit: Habit) -> Habit:
        habit.is_active = False
        habit.is_deleted = True
        habit.deleted_at = datetime.now(timezone.utc)
        await self._session.flush()
        return habit

    async def count_active_habits(self, user_id: int) -> int:
        statement = select(func.count(Habit.id)).where(
            Habit.user_id == user_id,
            Habit.is_active.is_(True),
            Habit.is_deleted.is_(False),
        )
        result = await self._session.scalar(statement)
        return int(result or 0)
