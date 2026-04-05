from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from app.repositories.habit_log_repository import HabitLogRepository
from app.repositories.habit_repository import HabitRepository
from app.services.habit_schedule_service import HabitScheduleService


@dataclass(slots=True)
class DueHabitReminder:
    habit_id: int
    telegram_id: int
    habit_title: str


class ReminderService:
    def __init__(
        self,
        habit_repository: HabitRepository,
        habit_log_repository: HabitLogRepository,
    ) -> None:
        self._habit_repository = habit_repository
        self._habit_log_repository = habit_log_repository

    async def get_due_habit_reminders(
        self,
        current_utc_datetime: datetime,
    ) -> list[DueHabitReminder]:
        due_habits = await self._habit_repository.get_habits_for_reminder_check()
        reminders: list[DueHabitReminder] = []

        normalized_utc_datetime = self.normalize_utc_datetime(current_utc_datetime)

        for habit in due_habits:
            if habit.user is None or habit.user.utc_offset_minutes is None:
                continue
            if habit.reminder_time is None:
                continue

            user_local_datetime = self.get_user_local_datetime(
                normalized_utc_datetime,
                habit.user.utc_offset_minutes,
            )
            user_local_date = user_local_datetime.date()
            user_local_time = time(
                hour=user_local_datetime.hour,
                minute=user_local_datetime.minute,
            )

            if habit.reminder_time != user_local_time:
                continue

            if not HabitScheduleService.is_habit_due_on_date(habit, user_local_date):
                continue

            is_completed_today = await self._habit_log_repository.is_completed_for_date(
                habit.id,
                user_local_date,
            )
            if is_completed_today:
                continue

            reminders.append(
                DueHabitReminder(
                    habit_id=habit.id,
                    telegram_id=habit.user.telegram_id,
                    habit_title=habit.title,
                )
            )

        return reminders

    @staticmethod
    def normalize_utc_datetime(target_datetime: datetime | None = None) -> datetime:
        current_datetime = target_datetime or datetime.now(timezone.utc)
        normalized_datetime = current_datetime.astimezone(timezone.utc)
        return normalized_datetime.replace(second=0, microsecond=0)

    @staticmethod
    def get_user_local_datetime(
        current_utc_datetime: datetime,
        utc_offset_minutes: int,
    ) -> datetime:
        return current_utc_datetime + timedelta(minutes=utc_offset_minutes)
