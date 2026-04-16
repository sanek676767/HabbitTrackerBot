from datetime import date, datetime, time, timezone

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
        *,
        frequency_type: str = "daily",
        frequency_interval: int | None = None,
        week_days_mask: int | None = None,
        start_date: date | None = None,
        reminder_enabled: bool = False,
        reminder_time: time | None = None,
        goal_type: str | None = None,
        goal_target_value: int | None = None,
        goal_achieved_at: datetime | None = None,
    ) -> Habit:
        habit = Habit(
            user_id=user_id,
            title=title,
            frequency_type=frequency_type,
            frequency_interval=frequency_interval,
            week_days_mask=week_days_mask,
            start_date=start_date or date.today(),
            reminder_enabled=reminder_enabled,
            reminder_time=reminder_time,
            goal_type=goal_type,
            goal_target_value=goal_target_value,
            goal_achieved_at=goal_achieved_at,
        )
        self._session.add(habit)
        await self._session.flush()
        return habit

    async def get_active_habits_by_user(
        self,
        user_id: int,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Habit]:
        statement = (
            select(Habit)
            .where(
                Habit.user_id == user_id,
                Habit.is_active.is_(True),
                Habit.is_deleted.is_(False),
            )
            .order_by(Habit.created_at.asc(), Habit.id.asc())
        )
        statement = self._apply_pagination(statement, limit=limit, offset=offset)
        result = await self._session.scalars(statement)
        return list(result)

    async def get_archived_habits_by_user(
        self,
        user_id: int,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Habit]:
        statement = (
            select(Habit)
            .where(
                Habit.user_id == user_id,
                Habit.is_active.is_(False),
                Habit.is_deleted.is_(False),
            )
            .order_by(Habit.updated_at.desc(), Habit.id.desc())
        )
        statement = self._apply_pagination(statement, limit=limit, offset=offset)
        result = await self._session.scalars(statement)
        return list(result)

    async def get_deleted_habits_by_user(
        self,
        user_id: int,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Habit]:
        statement = (
            select(Habit)
            .options(selectinload(Habit.user))
            .where(
                Habit.user_id == user_id,
                Habit.is_deleted.is_(True),
            )
            .order_by(Habit.deleted_at.desc(), Habit.id.desc())
        )
        statement = self._apply_pagination(statement, limit=limit, offset=offset)
        result = await self._session.scalars(statement)
        return list(result)

    async def get_deleted_habits(
        self,
        *,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Habit]:
        statement = (
            select(Habit)
            .options(selectinload(Habit.user))
            .where(Habit.is_deleted.is_(True))
            .order_by(Habit.deleted_at.desc(), Habit.id.desc())
        )
        statement = self._apply_pagination(statement, limit=limit, offset=offset)
        result = await self._session.scalars(statement)
        return list(result)

    async def get_habit_by_id(self, habit_id: int) -> Habit | None:
        statement = (
            select(Habit)
            .options(selectinload(Habit.user))
            .where(Habit.id == habit_id)
        )
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

    async def restore_soft_deleted_habit(self, habit: Habit) -> Habit:
        habit.is_deleted = False
        habit.deleted_at = None
        habit.is_active = False
        await self._session.flush()
        return habit

    async def update_title(self, habit: Habit, title: str) -> Habit:
        habit.title = title
        await self._session.flush()
        return habit

    async def update_schedule(
        self,
        habit: Habit,
        *,
        frequency_type: str,
        frequency_interval: int | None,
        week_days_mask: int | None,
        start_date: date,
    ) -> Habit:
        habit.frequency_type = frequency_type
        habit.frequency_interval = frequency_interval
        habit.week_days_mask = week_days_mask
        habit.start_date = start_date
        await self._session.flush()
        return habit

    async def update_last_completed_at(self, habit: Habit, last_completed_at: datetime) -> Habit:
        habit.last_completed_at = last_completed_at
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

    async def update_goal(
        self,
        habit: Habit,
        *,
        goal_type: str,
        goal_target_value: int,
        goal_achieved_at: datetime | None,
    ) -> Habit:
        habit.goal_type = goal_type
        habit.goal_target_value = goal_target_value
        habit.goal_achieved_at = goal_achieved_at
        await self._session.flush()
        return habit

    async def clear_goal(self, habit: Habit) -> Habit:
        habit.goal_type = None
        habit.goal_target_value = None
        habit.goal_achieved_at = None
        await self._session.flush()
        return habit

    async def update_goal_achieved_at(
        self,
        habit: Habit,
        goal_achieved_at: datetime | None,
    ) -> Habit:
        habit.goal_achieved_at = goal_achieved_at
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

    async def get_last_completed_habits_by_user(
        self,
        user_id: int,
        *,
        limit: int = 1,
    ) -> list[Habit]:
        statement = (
            select(Habit)
            .where(
                Habit.user_id == user_id,
                Habit.is_deleted.is_(False),
                Habit.last_completed_at.is_not(None),
            )
            .order_by(Habit.last_completed_at.desc(), Habit.id.desc())
            .limit(limit)
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

    async def count_archived_habits(self, user_id: int) -> int:
        statement = select(func.count(Habit.id)).where(
            Habit.user_id == user_id,
            Habit.is_active.is_(False),
            Habit.is_deleted.is_(False),
        )
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def count_deleted_habits(self, user_id: int | None = None) -> int:
        statement = select(func.count(Habit.id)).where(Habit.is_deleted.is_(True))
        if user_id is not None:
            statement = statement.where(Habit.user_id == user_id)
        result = await self._session.scalar(statement)
        return int(result or 0)

    @staticmethod
    def _apply_pagination(statement, *, limit: int | None, offset: int):
        if limit is None:
            return statement
        return statement.limit(limit).offset(offset)
