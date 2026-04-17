"""Валидация расписаний и расчёт серий по привычкам."""

from dataclasses import dataclass
from datetime import date, timedelta


WEEKDAY_LABELS = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
WEEKDAY_BUTTON_LABELS = ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс")
WEEKDAY_BIT_VALUES = tuple(1 << index for index in range(7))


class HabitScheduleValidationError(Exception):
    pass


@dataclass(slots=True)
class HabitScheduleConfig:
    frequency_type: str
    frequency_interval: int | None
    week_days_mask: int | None
    start_date: date


class HabitScheduleService:
    DAILY = "daily"
    INTERVAL = "interval"
    WEEKDAYS = "weekdays"

    EVERY_OTHER_DAY_INTERVAL = 2

    @classmethod
    def validate_schedule(
        cls,
        *,
        frequency_type: str,
        frequency_interval: int | None = None,
        week_days_mask: int | None = None,
        start_date: date | None = None,
    ) -> HabitScheduleConfig:
        normalized_start_date = start_date or date.today()

        if frequency_type == cls.DAILY:
            return HabitScheduleConfig(
                frequency_type=cls.DAILY,
                frequency_interval=None,
                week_days_mask=None,
                start_date=normalized_start_date,
            )

        if frequency_type == cls.INTERVAL:
            interval = frequency_interval or cls.EVERY_OTHER_DAY_INTERVAL
            if interval < 2:
                raise HabitScheduleValidationError(
                    "Для такого расписания интервал должен быть не меньше двух дней."
                )
            return HabitScheduleConfig(
                frequency_type=cls.INTERVAL,
                frequency_interval=interval,
                week_days_mask=None,
                start_date=normalized_start_date,
            )

        if frequency_type == cls.WEEKDAYS:
            if week_days_mask is None or week_days_mask <= 0:
                raise HabitScheduleValidationError("Выбери хотя бы один день недели.")
            return HabitScheduleConfig(
                frequency_type=cls.WEEKDAYS,
                frequency_interval=None,
                week_days_mask=week_days_mask,
                start_date=normalized_start_date,
            )

        raise HabitScheduleValidationError("Не удалось определить расписание привычки.")

    @classmethod
    def is_habit_due_on_date(cls, habit, target_date: date) -> bool:
        schedule = cls._get_schedule_config(habit)
        if target_date < schedule.start_date:
            return False

        if schedule.frequency_type == cls.DAILY:
            return True

        if schedule.frequency_type == cls.INTERVAL:
            interval = schedule.frequency_interval or cls.EVERY_OTHER_DAY_INTERVAL
            # Интервальные расписания привязаны к `start_date`.
            return (target_date - schedule.start_date).days % interval == 0

        if schedule.frequency_type == cls.WEEKDAYS:
            return cls.is_weekday_selected(
                schedule.week_days_mask,
                target_date.weekday(),
            )

        return False

    @classmethod
    def count_due_dates(
        cls,
        habit,
        start_date: date,
        end_date: date,
    ) -> int:
        return len(cls.get_due_dates(habit, start_date, end_date))

    @classmethod
    def get_due_dates(
        cls,
        habit,
        start_date: date,
        end_date: date,
    ) -> list[date]:
        if end_date < start_date:
            return []

        schedule = cls._get_schedule_config(habit)
        effective_start = max(start_date, schedule.start_date)
        if effective_start > end_date:
            return []

        if schedule.frequency_type == cls.DAILY:
            return [
                effective_start + timedelta(days=offset)
                for offset in range((end_date - effective_start).days + 1)
            ]

        if schedule.frequency_type == cls.INTERVAL:
            interval = schedule.frequency_interval or cls.EVERY_OTHER_DAY_INTERVAL
            offset_from_start = (effective_start - schedule.start_date).days
            remainder = offset_from_start % interval
            first_due_date = (
                effective_start
                if remainder == 0
                else effective_start + timedelta(days=interval - remainder)
            )
            due_dates: list[date] = []
            cursor = first_due_date
            while cursor <= end_date:
                due_dates.append(cursor)
                cursor += timedelta(days=interval)
            return due_dates

        due_dates: list[date] = []
        cursor = effective_start
        while cursor <= end_date:
            if cls.is_weekday_selected(schedule.week_days_mask, cursor.weekday()):
                due_dates.append(cursor)
            cursor += timedelta(days=1)
        return due_dates

    @classmethod
    def get_latest_due_date_on_or_before(cls, habit, target_date: date) -> date | None:
        schedule = cls._get_schedule_config(habit)
        if target_date < schedule.start_date:
            return None

        if schedule.frequency_type == cls.DAILY:
            return target_date

        if schedule.frequency_type == cls.INTERVAL:
            interval = schedule.frequency_interval or cls.EVERY_OTHER_DAY_INTERVAL
            days_since_start = (target_date - schedule.start_date).days
            return target_date - timedelta(days=days_since_start % interval)

        cursor = target_date
        while cursor >= schedule.start_date:
            if cls.is_weekday_selected(schedule.week_days_mask, cursor.weekday()):
                return cursor
            cursor -= timedelta(days=1)
        return None

    @classmethod
    def calculate_current_streak(
        cls,
        habit,
        completion_dates: set[date],
        target_date: date,
    ) -> int:
        anchor_date = cls.get_latest_due_date_on_or_before(habit, target_date)
        if anchor_date is None:
            return 0

        if anchor_date not in completion_dates:
            anchor_date = cls.get_latest_due_date_on_or_before(
                habit,
                anchor_date - timedelta(days=1),
            )

        if anchor_date is None or anchor_date not in completion_dates:
            return 0

        streak = 0
        cursor = anchor_date
        while cursor is not None and cursor in completion_dates:
            streak += 1
            cursor = cls.get_latest_due_date_on_or_before(
                habit,
                cursor - timedelta(days=1),
            )
        return streak

    @classmethod
    def calculate_best_streak(
        cls,
        habit,
        completion_dates: set[date],
        target_date: date,
    ) -> int:
        if not completion_dates:
            return 0

        last_completion_date = max(completion_dates)
        due_dates = cls.get_due_dates(
            habit,
            cls._get_schedule_config(habit).start_date,
            max(target_date, last_completion_date),
        )
        streak = 0
        best_streak = 0
        for due_date in due_dates:
            if due_date in completion_dates:
                streak += 1
                best_streak = max(best_streak, streak)
            else:
                streak = 0
        return best_streak

    @classmethod
    def format_schedule(cls, habit) -> str:
        return cls.format_schedule_config(cls._get_schedule_config(habit))

    @classmethod
    def format_schedule_config(cls, schedule: HabitScheduleConfig) -> str:
        if schedule.frequency_type == cls.DAILY:
            return "ежедневно"

        if schedule.frequency_type == cls.INTERVAL:
            interval = schedule.frequency_interval or cls.EVERY_OTHER_DAY_INTERVAL
            if interval == 2:
                return "через день"
            return f"каждые {interval} дня"

        return cls.format_weekdays(schedule.week_days_mask)

    @classmethod
    def format_weekdays(cls, week_days_mask: int | None) -> str:
        selected_days = cls.decode_week_days_mask(week_days_mask)
        if not selected_days:
            return "дни не выбраны"
        return "/".join(WEEKDAY_LABELS[index] for index in selected_days)

    @classmethod
    def build_week_days_mask(cls, week_days: list[int] | set[int]) -> int:
        # Расписания по дням недели хранятся как компактная битовая маска,
        # чтобы и модель, и представление в БД оставались простыми.
        mask = 0
        for day_index in sorted(week_days):
            if day_index < 0 or day_index > 6:
                raise HabitScheduleValidationError("Не удалось определить дни недели.")
            mask |= WEEKDAY_BIT_VALUES[day_index]
        return mask

    @classmethod
    def decode_week_days_mask(cls, week_days_mask: int | None) -> list[int]:
        if not week_days_mask:
            return []
        return [
            index
            for index in range(7)
            if cls.is_weekday_selected(week_days_mask, index)
        ]

    @staticmethod
    def is_weekday_selected(week_days_mask: int | None, weekday_index: int) -> bool:
        if week_days_mask is None:
            return False
        return bool(week_days_mask & (1 << weekday_index))

    @classmethod
    def _get_schedule_config(cls, habit) -> HabitScheduleConfig:
        return cls.validate_schedule(
            frequency_type=habit.frequency_type,
            frequency_interval=getattr(habit, "frequency_interval", None),
            week_days_mask=getattr(habit, "week_days_mask", None),
            start_date=getattr(habit, "start_date", None),
        )
