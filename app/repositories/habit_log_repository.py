"""Хелперы доступа к данным логов выполнения привычек."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit
from app.models.habit_log import HabitLog


class HabitLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_log(self, habit_id: int, completed_for_date: date) -> HabitLog:
        habit_log = HabitLog(
            habit_id=habit_id,
            completed_for_date=completed_for_date,
        )
        self._session.add(habit_log)
        await self._session.flush()
        return habit_log

    async def is_completed_for_date(self, habit_id: int, completed_for_date: date) -> bool:
        statement = select(HabitLog.id).where(
            HabitLog.habit_id == habit_id,
            HabitLog.completed_for_date == completed_for_date,
        )
        result = await self._session.scalar(statement)
        return result is not None

    async def count_completions(self, habit_id: int) -> int:
        statement = select(func.count(HabitLog.id)).where(HabitLog.habit_id == habit_id)
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def count_completed_today_for_user(self, user_id: int, target_date: date) -> int:
        statement = (
            select(func.count(HabitLog.id))
            .select_from(HabitLog)
            .join(Habit, Habit.id == HabitLog.habit_id)
            .where(
                Habit.user_id == user_id,
                Habit.is_active.is_(True),
                Habit.is_deleted.is_(False),
                HabitLog.completed_for_date == target_date,
            )
        )
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def count_completed_by_user_for_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        *,
        active_only: bool = True,
    ) -> int:
        statement = (
            select(func.count(HabitLog.id))
            .select_from(HabitLog)
            .join(Habit, Habit.id == HabitLog.habit_id)
            .where(
                Habit.user_id == user_id,
                Habit.is_deleted.is_(False),
                HabitLog.completed_for_date >= start_date,
                HabitLog.completed_for_date <= end_date,
            )
        )
        if active_only:
            statement = statement.where(Habit.is_active.is_(True))

        result = await self._session.scalar(statement)
        return int(result or 0)

    async def get_completed_habit_ids_for_user_by_date(
        self,
        user_id: int,
        target_date: date,
    ) -> list[int]:
        statement = (
            select(HabitLog.habit_id)
            .join(Habit, Habit.id == HabitLog.habit_id)
            .where(
                Habit.user_id == user_id,
                Habit.is_active.is_(True),
                Habit.is_deleted.is_(False),
                HabitLog.completed_for_date == target_date,
            )
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def get_completion_dates(self, habit_id: int) -> list[date]:
        statement = (
            select(HabitLog.completed_for_date)
            .where(HabitLog.habit_id == habit_id)
            .order_by(HabitLog.completed_for_date.asc())
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def get_completion_dates_for_habit_ids(
        self,
        habit_ids: list[int],
    ) -> list[tuple[int, date]]:
        if not habit_ids:
            return []

        statement = (
            select(HabitLog.habit_id, HabitLog.completed_for_date)
            .where(HabitLog.habit_id.in_(habit_ids))
            .order_by(HabitLog.habit_id.asc(), HabitLog.completed_for_date.asc())
        )
        result = await self._session.execute(statement)
        return list(result.all())

    async def get_completion_counts_by_habit_for_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        *,
        active_only: bool = True,
    ) -> list[tuple[int, str, int]]:
        completion_count = func.count(HabitLog.id).filter(
            HabitLog.completed_for_date >= start_date,
            HabitLog.completed_for_date <= end_date,
        )
        statement = (
            select(
                Habit.id,
                Habit.title,
                completion_count,
            )
            .select_from(Habit)
            .join(HabitLog, HabitLog.habit_id == Habit.id, isouter=True)
            .where(
                Habit.user_id == user_id,
                Habit.is_deleted.is_(False),
            )
            .group_by(Habit.id, Habit.title)
            .order_by(Habit.id.asc())
        )
        if active_only:
            statement = statement.where(Habit.is_active.is_(True))

        result = await self._session.execute(statement)
        return [
            (habit_id, title, int(completions or 0))
            for habit_id, title, completions in result.all()
        ]
