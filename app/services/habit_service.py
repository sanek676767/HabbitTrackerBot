import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.habit import Habit, HabitFrequencyType
from app.repositories.habit_log_repository import HabitLogRepository
from app.repositories.habit_repository import HabitRepository


TITLE_MAX_LENGTH = 100
LAST_7_DAYS_WINDOW = 7
REMINDER_TIME_PATTERN = re.compile(r"^\d{2}:\d{2}$")


class HabitServiceError(Exception):
    pass


class HabitValidationError(HabitServiceError):
    pass


class HabitReminderValidationError(HabitServiceError):
    pass


class HabitNotFoundError(HabitServiceError):
    pass


class HabitArchivedError(HabitServiceError):
    pass


class HabitDeletedError(HabitServiceError):
    pass


class HabitAlreadyCompletedError(HabitServiceError):
    pass


@dataclass(slots=True)
class HabitListItem:
    id: int
    title: str
    is_completed_today: bool = False


@dataclass(slots=True)
class HabitReminderState:
    enabled: bool
    reminder_time: time | None


@dataclass(slots=True)
class HabitCard:
    id: int
    title: str
    is_completed_today: bool
    total_completions: int
    current_streak: int
    best_streak: int
    is_active: bool
    reminder_enabled: bool
    reminder_time: time | None


@dataclass(slots=True)
class HabitStats:
    id: int
    title: str
    total_completions: int
    is_completed_today: bool
    current_streak: int
    best_streak: int
    last_7_days_progress_text: str
    created_at: datetime


@dataclass(slots=True)
class HabitProgressSummary:
    total_completions: int
    is_completed_today: bool
    current_streak: int
    best_streak: int
    last_7_days_progress_text: str


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
        normalized_title = self._normalize_title(title)
        habit = await self._habit_repository.create_habit(
            user_id=user_id,
            title=normalized_title,
            frequency_type=HabitFrequencyType.DAILY.value,
        )
        await self._session.commit()
        await self._session.refresh(habit)
        return habit

    async def rename_habit(self, user_id: int, habit_id: int, title: str) -> HabitCard:
        habit = await self._get_visible_user_habit(user_id, habit_id)
        normalized_title = self._normalize_title(title)

        await self._habit_repository.update_title(habit, normalized_title)
        await self._session.commit()
        await self._session.refresh(habit)
        return await self.get_habit_card(user_id, habit_id)

    async def enable_reminder(
        self,
        user_id: int,
        habit_id: int,
        reminder_time: str,
    ) -> HabitReminderState:
        habit = await self._get_visible_user_habit(user_id, habit_id)
        self._ensure_reminder_can_be_enabled(habit)

        parsed_time = self._parse_reminder_time(reminder_time)
        await self._habit_repository.update_reminder(
            habit,
            enabled=True,
            reminder_time=parsed_time,
        )
        await self._session.commit()
        return HabitReminderState(enabled=True, reminder_time=parsed_time)

    async def disable_reminder(self, user_id: int, habit_id: int) -> HabitReminderState:
        habit = await self._get_visible_user_habit(user_id, habit_id)
        await self._habit_repository.update_reminder(
            habit,
            enabled=False,
            reminder_time=None,
        )
        await self._session.commit()
        return HabitReminderState(enabled=False, reminder_time=None)

    async def update_reminder_time(
        self,
        user_id: int,
        habit_id: int,
        reminder_time: str,
    ) -> HabitReminderState:
        habit = await self._get_visible_user_habit(user_id, habit_id)
        self._ensure_reminder_can_be_enabled(habit)

        parsed_time = self._parse_reminder_time(reminder_time)
        await self._habit_repository.update_reminder(
            habit,
            enabled=True,
            reminder_time=parsed_time,
        )
        await self._session.commit()
        return HabitReminderState(enabled=True, reminder_time=parsed_time)

    async def get_habit_reminder_state(self, user_id: int, habit_id: int) -> HabitReminderState:
        habit = await self._get_visible_user_habit(user_id, habit_id)
        return HabitReminderState(
            enabled=habit.reminder_enabled,
            reminder_time=habit.reminder_time,
        )

    async def get_active_habits(self, user_id: int) -> list[HabitListItem]:
        habits = await self._habit_repository.get_active_habits_by_user(user_id)
        return [HabitListItem(id=habit.id, title=habit.title) for habit in habits]

    async def get_archived_habits(self, user_id: int) -> list[HabitListItem]:
        habits = await self._habit_repository.get_archived_habits_by_user(user_id)
        return [HabitListItem(id=habit.id, title=habit.title) for habit in habits]

    async def get_habit_card(self, user_id: int, habit_id: int) -> HabitCard:
        habit = await self._get_visible_user_habit(user_id, habit_id)
        progress = await self._build_progress_summary(habit.id)
        return HabitCard(
            id=habit.id,
            title=habit.title,
            is_completed_today=progress.is_completed_today,
            total_completions=progress.total_completions,
            current_streak=progress.current_streak,
            best_streak=progress.best_streak,
            is_active=habit.is_active,
            reminder_enabled=habit.reminder_enabled,
            reminder_time=habit.reminder_time,
        )

    async def complete_habit_for_today(self, user_id: int, habit_id: int) -> HabitCard:
        habit = await self._get_visible_user_habit(user_id, habit_id)
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
        habit = await self._get_visible_user_habit(user_id, habit_id)
        progress = await self._build_progress_summary(habit.id)
        return HabitStats(
            id=habit.id,
            title=habit.title,
            total_completions=progress.total_completions,
            is_completed_today=progress.is_completed_today,
            current_streak=progress.current_streak,
            best_streak=progress.best_streak,
            last_7_days_progress_text=progress.last_7_days_progress_text,
            created_at=habit.created_at,
        )

    async def archive_habit(self, user_id: int, habit_id: int) -> bool:
        habit = await self._get_visible_user_habit(user_id, habit_id)
        if not habit.is_active:
            return False

        await self._habit_repository.archive_habit(habit)
        await self._session.commit()
        return True

    async def restore_habit(self, user_id: int, habit_id: int) -> bool:
        habit = await self._get_visible_user_habit(user_id, habit_id)
        if habit.is_active:
            return False

        await self._habit_repository.restore_habit(habit)
        await self._session.commit()
        return True

    async def soft_delete_habit(self, user_id: int, habit_id: int) -> bool:
        habit = await self._get_user_habit(user_id, habit_id)
        if habit.is_deleted:
            raise HabitDeletedError("Привычка уже удалена.")

        await self._habit_repository.soft_delete_habit(habit)
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

    async def _build_progress_summary(self, habit_id: int) -> HabitProgressSummary:
        completion_dates = await self._habit_log_repository.get_completion_dates(habit_id)
        completion_date_set = set(completion_dates)
        today = self._get_today()

        return HabitProgressSummary(
            total_completions=len(completion_dates),
            is_completed_today=today in completion_date_set,
            current_streak=self._calculate_current_streak(completion_date_set, today),
            best_streak=self._calculate_best_streak(completion_dates),
            last_7_days_progress_text=self._build_last_7_days_progress_text(
                completion_date_set,
                today,
            ),
        )

    async def _get_visible_user_habit(self, user_id: int, habit_id: int) -> Habit:
        habit = await self._get_user_habit(user_id, habit_id)
        if habit.is_deleted:
            raise HabitDeletedError("Привычка удалена.")
        return habit

    async def _get_user_habit(self, user_id: int, habit_id: int) -> Habit:
        habit = await self._habit_repository.get_habit_by_id_for_user(habit_id, user_id)
        if habit is None:
            raise HabitNotFoundError("Привычка не найдена.")
        return habit

    @staticmethod
    def _normalize_title(title: str) -> str:
        normalized_title = title.strip()
        if not normalized_title:
            raise HabitValidationError("Название привычки не может быть пустым.")
        if len(normalized_title) > TITLE_MAX_LENGTH:
            raise HabitValidationError(
                f"Название привычки должно быть не длиннее {TITLE_MAX_LENGTH} символов."
            )
        return normalized_title

    @staticmethod
    def _parse_reminder_time(raw_time: str) -> time:
        normalized_time = raw_time.strip()
        if not REMINDER_TIME_PATTERN.fullmatch(normalized_time):
            raise HabitReminderValidationError("Введите время в формате ЧЧ:ММ.")

        hours, minutes = normalized_time.split(":")
        hour = int(hours)
        minute = int(minutes)

        if hour > 23 or minute > 59:
            raise HabitReminderValidationError("Введите корректное время в формате ЧЧ:ММ.")

        return time(hour=hour, minute=minute)

    @staticmethod
    def _calculate_current_streak(completion_dates: set[date], today: date) -> int:
        if today in completion_dates:
            anchor_date = today
        elif today - timedelta(days=1) in completion_dates:
            anchor_date = today - timedelta(days=1)
        else:
            return 0

        streak = 0
        cursor = anchor_date
        while cursor in completion_dates:
            streak += 1
            cursor -= timedelta(days=1)
        return streak

    @staticmethod
    def _calculate_best_streak(completion_dates: list[date]) -> int:
        if not completion_dates:
            return 0

        best_streak = 1
        current_streak = 1

        for previous_date, current_date in zip(completion_dates, completion_dates[1:]):
            if current_date == previous_date + timedelta(days=1):
                current_streak += 1
            else:
                best_streak = max(best_streak, current_streak)
                current_streak = 1

        return max(best_streak, current_streak)

    @staticmethod
    def _build_last_7_days_progress_text(completion_dates: set[date], today: date) -> str:
        days = [
            today - timedelta(days=offset)
            for offset in reversed(range(LAST_7_DAYS_WINDOW))
        ]
        return "\n".join(
            f"{day.strftime('%d.%m')}: {'✅' if day in completion_dates else '⬜'}"
            for day in days
        )

    @staticmethod
    def _ensure_reminder_can_be_enabled(habit: Habit) -> None:
        if not habit.is_active:
            raise HabitArchivedError("Для архивной привычки нельзя включить напоминание.")

    @staticmethod
    def _get_today() -> date:
        return date.today()
