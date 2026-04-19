"""Агрегированные метрики прогресса для экранов и сводок."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.habit_log_repository import HabitLogRepository
from app.repositories.habit_repository import HabitRepository
from app.services.habit_schedule_service import HabitScheduleService


SEVEN_DAY_WINDOW = 7
THIRTY_DAY_WINDOW = 30


@dataclass(slots=True)
class CompletionRate:
    days: int
    completed: int
    total_possible: int
    percentage: float


@dataclass(slots=True)
class LastCompletedHabit:
    id: int
    title: str
    last_completed_at: datetime


@dataclass(slots=True)
class HabitStreakSnapshot:
    habit_id: int
    title: str
    current_streak: int
    best_streak: int


@dataclass(slots=True)
class DailyProgressSummary:
    active_habits_count: int
    due_today_count: int
    completed_today_count: int
    remaining_today_count: int


@dataclass(slots=True)
class WeeklyProgressSummary:
    total_completions: int
    average_completion_rate: float
    best_habit_title: str | None
    best_habit_completion_count: int
    best_streak_habit_title: str | None
    best_streak_value: int
    problem_habits: list[str]


@dataclass(slots=True)
class ProgressScreenData:
    active_habits_count: int
    due_today_count: int
    completed_today_count: int
    remaining_today_count: int
    completion_rate_7_days: float
    completion_rate_30_days: float
    best_current_streak_habit_title: str | None
    best_current_streak_value: int
    last_completed_habit_title: str | None
    last_completed_at: datetime | None


class ProgressService:
    def __init__(
        self,
        session: AsyncSession,
        habit_repository: HabitRepository,
        habit_log_repository: HabitLogRepository,
    ) -> None:
        self._session = session
        self._habit_repository = habit_repository
        self._habit_log_repository = habit_log_repository

    async def get_daily_progress_summary(
        self,
        user_id: int,
        target_date: date | None = None,
    ) -> DailyProgressSummary:
        summary_date = target_date or self._get_today()
        active_habits = self._exclude_paused_habits(
            await self._habit_repository.get_active_habits_by_user(user_id)
        )
        due_today_habits = [
            habit
            for habit in active_habits
            if HabitScheduleService.is_habit_due_on_date(habit, summary_date)
        ]
        completed_ids = set(
            await self._habit_log_repository.get_completed_habit_ids_for_user_by_date(
                user_id,
                summary_date,
            )
        )
        completed_today_count = sum(
            1
            for habit in due_today_habits
            if habit.id in completed_ids
        )
        due_today_count = len(due_today_habits)
        remaining_today_count = max(due_today_count - completed_today_count, 0)
        return DailyProgressSummary(
            active_habits_count=len(active_habits),
            due_today_count=due_today_count,
            completed_today_count=completed_today_count,
            remaining_today_count=remaining_today_count,
        )

    async def get_weekly_progress_summary(
        self,
        user_id: int,
        target_date: date | None = None,
    ) -> WeeklyProgressSummary:
        summary_date = target_date or self._get_today()
        week_start = summary_date - timedelta(days=SEVEN_DAY_WINDOW - 1)
        active_habits = self._exclude_paused_habits(
            await self._habit_repository.get_active_habits_by_user(user_id)
        )
        weekly_counts = await self._get_completion_count_map_for_period(
            active_habits,
            week_start,
            summary_date,
        )
        total_completions = sum(weekly_counts.values())
        weekly_rate = await self.get_completion_rate(user_id, SEVEN_DAY_WINDOW, summary_date)
        streak_snapshots = await self._get_active_habit_streak_snapshots(active_habits, summary_date)

        best_habit_title = None
        best_habit_completion_count = 0
        if weekly_counts:
            best_habit = max(
                active_habits,
                key=lambda habit: (weekly_counts.get(habit.id, 0), -habit.id),
            )
            best_habit_completion_count = weekly_counts.get(best_habit.id, 0)
            if best_habit_completion_count > 0:
                best_habit_title = best_habit.title

        best_streak_habit_title = None
        best_streak_value = 0
        if streak_snapshots:
            best_streak_snapshot = max(
                streak_snapshots,
                key=lambda snapshot: (snapshot.best_streak, snapshot.current_streak, -snapshot.habit_id),
            )
            if best_streak_snapshot.best_streak > 0:
                best_streak_habit_title = best_streak_snapshot.title
                best_streak_value = best_streak_snapshot.best_streak

        problem_habits = [
            habit.title
            for habit in active_habits
            if HabitScheduleService.count_due_dates(habit, week_start, summary_date) > 0
            and weekly_counts.get(habit.id, 0) == 0
        ][:3]

        return WeeklyProgressSummary(
            total_completions=total_completions,
            average_completion_rate=weekly_rate.percentage,
            best_habit_title=best_habit_title,
            best_habit_completion_count=best_habit_completion_count,
            best_streak_habit_title=best_streak_habit_title,
            best_streak_value=best_streak_value,
            problem_habits=problem_habits,
        )

    async def get_progress_screen_data(
        self,
        user_id: int,
        target_date: date | None = None,
    ) -> ProgressScreenData:
        progress_date = target_date or self._get_today()
        daily_summary = await self.get_daily_progress_summary(user_id, progress_date)
        rate_7_days = await self.get_completion_rate(user_id, SEVEN_DAY_WINDOW, progress_date)
        rate_30_days = await self.get_completion_rate(user_id, THIRTY_DAY_WINDOW, progress_date)
        active_habits = self._exclude_paused_habits(
            await self._habit_repository.get_active_habits_by_user(user_id)
        )
        streak_snapshots = await self._get_active_habit_streak_snapshots(active_habits, progress_date)
        last_completed_habits = await self.get_last_completed_habits(user_id, limit=1)

        best_current_streak_habit_title = None
        best_current_streak_value = 0
        if streak_snapshots:
            best_current_streak_snapshot = max(
                streak_snapshots,
                key=lambda snapshot: (snapshot.current_streak, snapshot.best_streak, -snapshot.habit_id),
            )
            if best_current_streak_snapshot.current_streak > 0:
                best_current_streak_habit_title = best_current_streak_snapshot.title
                best_current_streak_value = best_current_streak_snapshot.current_streak

        last_completed_habit_title = None
        last_completed_at = None
        if last_completed_habits:
            last_completed_habit_title = last_completed_habits[0].title
            last_completed_at = last_completed_habits[0].last_completed_at

        return ProgressScreenData(
            active_habits_count=daily_summary.active_habits_count,
            due_today_count=daily_summary.due_today_count,
            completed_today_count=daily_summary.completed_today_count,
            remaining_today_count=daily_summary.remaining_today_count,
            completion_rate_7_days=rate_7_days.percentage,
            completion_rate_30_days=rate_30_days.percentage,
            best_current_streak_habit_title=best_current_streak_habit_title,
            best_current_streak_value=best_current_streak_value,
            last_completed_habit_title=last_completed_habit_title,
            last_completed_at=last_completed_at,
        )

    async def get_completion_rate(
        self,
        user_id: int,
        days: int,
        target_date: date | None = None,
    ) -> CompletionRate:
        rate_end_date = target_date or self._get_today()
        rate_start_date = rate_end_date - timedelta(days=days - 1)
        active_habits = self._exclude_paused_habits(
            await self._habit_repository.get_active_habits_by_user(user_id)
        )
        completed_map = await self._get_completion_count_map_for_period(
            active_habits,
            rate_start_date,
            rate_end_date,
        )
        completed = sum(completed_map.values())
        total_possible = sum(
            HabitScheduleService.count_due_dates(habit, rate_start_date, rate_end_date)
            for habit in active_habits
        )
        percentage = round((completed / total_possible) * 100, 1) if total_possible else 0.0
        return CompletionRate(
            days=days,
            completed=completed,
            total_possible=total_possible,
            percentage=percentage,
        )

    async def get_completion_rates(
        self,
        user_id: int,
        target_date: date | None = None,
    ) -> tuple[CompletionRate, CompletionRate]:
        summary_date = target_date or self._get_today()
        rate_7_days = await self.get_completion_rate(user_id, SEVEN_DAY_WINDOW, summary_date)
        rate_30_days = await self.get_completion_rate(user_id, THIRTY_DAY_WINDOW, summary_date)
        return rate_7_days, rate_30_days

    async def get_last_completed_habits(
        self,
        user_id: int,
        *,
        limit: int = 1,
    ) -> list[LastCompletedHabit]:
        habits = self._exclude_paused_habits(
            await self._habit_repository.get_active_habits_by_user(user_id)
        )
        habits = sorted(
            (
                habit
                for habit in habits
                if getattr(habit, "last_completed_at", None) is not None
            ),
            key=lambda habit: (habit.last_completed_at, habit.id),
            reverse=True,
        )[:limit]
        return [
            LastCompletedHabit(
                id=habit.id,
                title=habit.title,
                last_completed_at=habit.last_completed_at,
            )
            for habit in habits
        ]

    @staticmethod
    def _exclude_paused_habits(habits: list) -> list:
        return [habit for habit in habits if not getattr(habit, "is_paused", False)]

    async def _get_active_habit_streak_snapshots(
        self,
        active_habits: list,
        target_date: date,
    ) -> list[HabitStreakSnapshot]:
        if not active_habits:
            return []

        habit_ids = [habit.id for habit in active_habits]
        completion_rows = await self._habit_log_repository.get_completion_dates_for_habit_ids(habit_ids)
        completion_dates_map: dict[int, list[date]] = defaultdict(list)
        for habit_id, completed_for_date in completion_rows:
            completion_dates_map[habit_id].append(completed_for_date)

        streak_snapshots: list[HabitStreakSnapshot] = []
        for habit in active_habits:
            completion_date_set = set(completion_dates_map.get(habit.id, []))
            streak_snapshots.append(
                HabitStreakSnapshot(
                    habit_id=habit.id,
                    title=habit.title,
                    current_streak=HabitScheduleService.calculate_current_streak(
                        habit,
                        completion_date_set,
                        target_date,
                    ),
                    best_streak=HabitScheduleService.calculate_best_streak(
                        habit,
                        completion_date_set,
                        target_date,
                    ),
                )
            )

        return streak_snapshots

    async def _get_completion_count_map_for_period(
        self,
        active_habits: list,
        start_date: date,
        end_date: date,
    ) -> dict[int, int]:
        if not active_habits:
            return {}

        habit_map = {habit.id: habit for habit in active_habits}
        completion_rows = await self._habit_log_repository.get_completion_dates_for_habit_ids(
            list(habit_map)
        )
        completion_count_map: dict[int, int] = defaultdict(int)
        for habit_id, completed_for_date in completion_rows:
            if completed_for_date < start_date or completed_for_date > end_date:
                continue
            habit = habit_map.get(habit_id)
            if habit is None:
                continue
            # В расчёт процентов и недельных сводок попадают только те
            # выполнения, которые пришлись на реально запланированные дни.
            if not HabitScheduleService.is_habit_due_on_date(habit, completed_for_date):
                continue
            completion_count_map[habit_id] += 1
        return dict(completion_count_map)

    @staticmethod
    def _get_today() -> date:
        return date.today()
