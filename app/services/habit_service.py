from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit, HabitFrequencyType
from app.repositories.habit_log_repository import HabitLogRepository
from app.repositories.habit_repository import HabitRepository


TITLE_MAX_LENGTH = 100


class HabitServiceError(Exception):
    pass


class HabitValidationError(HabitServiceError):
    pass


class HabitNotFoundError(HabitServiceError):
    pass


class HabitArchivedError(HabitServiceError):
    pass


class HabitAlreadyCompletedError(HabitServiceError):
    pass


@dataclass(slots=True)
class HabitListItem:
    id: int
    title: str
    is_completed_today: bool = False


@dataclass(slots=True)
class HabitCard:
    id: int
    title: str
    is_completed_today: bool
    total_completions: int
    is_active: bool


@dataclass(slots=True)
class HabitStats:
    id: int
    title: str
    total_completions: int
    is_completed_today: bool
    created_at: datetime


class HabitService:
    def __init__(
        self,
        session: AsyncSession,
        habit_repository: HabitRepository,
        habit_log_repository: HabitLogRepository,
    ) -> None:
        self._session = session
        self._habit_repository = habit_repository
        self._habit_log_repository = habit_log_repository

    async def create_habit(self, user_id: int, title: str) -> Habit:
        normalized_title = title.strip()
        if not normalized_title:
            raise HabitValidationError("Название привычки не может быть пустым.")
        if len(normalized_title) > TITLE_MAX_LENGTH:
            raise HabitValidationError(
                f"Название привычки должно быть не длиннее {TITLE_MAX_LENGTH} символов."
            )

        habit = await self._habit_repository.create_habit(
            user_id=user_id,
            title=normalized_title,
            frequency_type=HabitFrequencyType.DAILY.value,
        )
        await self._session.commit()
        await self._session.refresh(habit)
        return habit

    async def get_active_habits(self, user_id: int) -> list[HabitListItem]:
        habits = await self._habit_repository.get_active_habits_by_user(user_id)
        return [HabitListItem(id=habit.id, title=habit.title) for habit in habits]

    async def get_archived_habits(self, user_id: int) -> list[HabitListItem]:
        habits = await self._habit_repository.get_archived_habits_by_user(user_id)
        return [HabitListItem(id=habit.id, title=habit.title) for habit in habits]

    async def get_habit_card(self, user_id: int, habit_id: int) -> HabitCard:
        habit = await self._get_user_habit(user_id, habit_id)
        today = self._get_today()
        is_completed_today = await self._habit_log_repository.is_completed_for_date(habit.id, today)
        total_completions = await self._habit_log_repository.count_completions(habit.id)
        return HabitCard(
            id=habit.id,
            title=habit.title,
            is_completed_today=is_completed_today,
            total_completions=total_completions,
            is_active=habit.is_active,
        )

    async def complete_habit_for_today(self, user_id: int, habit_id: int) -> HabitCard:
        habit = await self._get_user_habit(user_id, habit_id)
        if not habit.is_active:
            raise HabitArchivedError("Архивную привычку нельзя отметить.")

        today = self._get_today()
        if await self._habit_log_repository.is_completed_for_date(habit.id, today):
            raise HabitAlreadyCompletedError("Эта привычка уже отмечена на сегодня.")

        try:
            await self._habit_log_repository.create_log(habit.id, today)
            await self._session.commit()
        except IntegrityError:
            await self._session.rollback()
            raise HabitAlreadyCompletedError("Эта привычка уже отмечена на сегодня.") from None

        return await self.get_habit_card(user_id, habit_id)

    async def get_habit_stats(self, user_id: int, habit_id: int) -> HabitStats:
        habit = await self._get_user_habit(user_id, habit_id)
        today = self._get_today()
        is_completed_today = await self._habit_log_repository.is_completed_for_date(habit.id, today)
        total_completions = await self._habit_log_repository.count_completions(habit.id)
        return HabitStats(
            id=habit.id,
            title=habit.title,
            total_completions=total_completions,
            is_completed_today=is_completed_today,
            created_at=habit.created_at,
        )

    async def archive_habit(self, user_id: int, habit_id: int) -> bool:
        habit = await self._get_user_habit(user_id, habit_id)
        if not habit.is_active:
            return False

        await self._habit_repository.archive_habit(habit)
        await self._session.commit()
        return True

    async def restore_habit(self, user_id: int, habit_id: int) -> bool:
        habit = await self._get_user_habit(user_id, habit_id)
        if habit.is_active:
            return False

        await self._habit_repository.restore_habit(habit)
        await self._session.commit()
        return True

    async def get_today_habits(self, user_id: int) -> list[HabitListItem]:
        today = self._get_today()
        habits = await self._habit_repository.get_active_habits_by_user(user_id)
        completed_ids = set(
            await self._habit_log_repository.get_completed_habit_ids_for_user_by_date(
                user_id,
                today,
            )
        )
        return [
            HabitListItem(
                id=habit.id,
                title=habit.title,
                is_completed_today=habit.id in completed_ids,
            )
            for habit in habits
        ]

    async def count_active_habits(self, user_id: int) -> int:
        return await self._habit_repository.count_active_habits(user_id)

    async def count_completed_today(self, user_id: int) -> int:
        return await self._habit_log_repository.count_completed_today_for_user(
            user_id,
            self._get_today(),
        )

    async def _get_user_habit(self, user_id: int, habit_id: int) -> Habit:
        habit = await self._habit_repository.get_habit_by_id_for_user(habit_id, user_id)
        if habit is None:
            raise HabitNotFoundError("Привычка не найдена.")
        return habit

    @staticmethod
    def _get_today() -> date:
        return date.today()
