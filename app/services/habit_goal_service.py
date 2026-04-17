"""Валидация целей и расчёт прогресса по привычкам."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from app.models.habit import HabitGoalType
from app.services.habit_schedule_service import HabitScheduleService


GOAL_MAX_TARGET_VALUE = 10_000


class HabitGoalValidationError(Exception):
    pass


@dataclass(slots=True)
class HabitGoalConfig:
    goal_type: str
    target_value: int


@dataclass(slots=True)
class HabitGoalProgress:
    goal_type: str
    target_value: int
    current_value: int
    goal_text: str
    progress_text: str
    is_achieved: bool
    status_text: str | None
    achieved_at: datetime | None


class HabitGoalService:
    COMPLETIONS = HabitGoalType.COMPLETIONS.value
    STREAK = HabitGoalType.STREAK.value

    @classmethod
    def validate_goal(
        cls,
        *,
        goal_type: str | None = None,
        goal_target_value: int | None = None,
    ) -> HabitGoalConfig | None:
        if goal_type is None and goal_target_value is None:
            return None

        if goal_type is None or goal_target_value is None:
            raise HabitGoalValidationError("Не удалось определить цель привычки.")

        if goal_type not in {cls.COMPLETIONS, cls.STREAK}:
            raise HabitGoalValidationError("Не удалось определить тип цели.")

        if goal_target_value < 1:
            raise HabitGoalValidationError("Цель должна быть больше нуля.")

        if goal_target_value > GOAL_MAX_TARGET_VALUE:
            raise HabitGoalValidationError(
                f"Цель должна быть не больше {GOAL_MAX_TARGET_VALUE}."
            )

        return HabitGoalConfig(
            goal_type=goal_type,
            target_value=goal_target_value,
        )

    @classmethod
    def get_goal_config(cls, habit) -> HabitGoalConfig | None:
        return cls.validate_goal(
            goal_type=getattr(habit, "goal_type", None),
            goal_target_value=getattr(habit, "goal_target_value", None),
        )

    @classmethod
    def calculate_progress(
        cls,
        habit,
        completion_dates: list[date] | set[date],
        target_date: date,
    ) -> HabitGoalProgress | None:
        config = cls.get_goal_config(habit)
        if config is None:
            return None

        completion_dates_list = sorted(
            item
            for item in completion_dates
            if item <= target_date
        )
        completion_dates_set = set(completion_dates_list)

        if config.goal_type == cls.COMPLETIONS:
            current_value = sum(1 for item in completion_dates_list if item <= target_date)
        else:
            current_value = HabitScheduleService.calculate_current_streak(
                habit,
                completion_dates_set,
                target_date,
            )

        is_achieved = bool(getattr(habit, "goal_achieved_at", None)) or current_value >= config.target_value
        return HabitGoalProgress(
            goal_type=config.goal_type,
            target_value=config.target_value,
            current_value=current_value,
            goal_text=cls.format_goal_config(config),
            progress_text=f"{current_value} / {config.target_value}",
            is_achieved=is_achieved,
            status_text="цель достигнута" if is_achieved else None,
            achieved_at=getattr(habit, "goal_achieved_at", None),
        )

    @classmethod
    def resolve_goal_achieved_at(
        cls,
        habit,
        progress: HabitGoalProgress | None,
        now: datetime | None = None,
    ) -> datetime | None:
        if progress is None:
            return None

        current_value = progress.current_value
        if current_value < progress.target_value:
            return getattr(habit, "goal_achieved_at", None)

        achieved_at = getattr(habit, "goal_achieved_at", None)
        if achieved_at is not None:
            # После достижения цели сохраняем исходную временную метку, а не
            # передвигаем его при каждом следующем пересчёте.
            return achieved_at

        return now or datetime.now(timezone.utc)

    @classmethod
    def format_goal(cls, habit) -> str | None:
        config = cls.get_goal_config(habit)
        if config is None:
            return None
        return cls.format_goal_config(config)

    @classmethod
    def format_goal_config(cls, config: HabitGoalConfig) -> str:
        if config.goal_type == cls.COMPLETIONS:
            return f"{config.target_value} {cls._pluralize(config.target_value, 'выполнение', 'выполнения', 'выполнений')}"

        return f"серия {config.target_value} {cls._pluralize(config.target_value, 'день', 'дня', 'дней')}"

    @staticmethod
    def _pluralize(value: int, one: str, few: str, many: str) -> str:
        tail = value % 100
        if 11 <= tail <= 14:
            return many

        tail = value % 10
        if tail == 1:
            return one
        if 2 <= tail <= 4:
            return few
        return many
