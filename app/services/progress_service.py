from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.habit_log_repository import HabitLogRepository
from app.repositories.habit_repository import HabitRepository


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
        active_habits_count = await self._habit_repository.count_active_habits(user_id)
        completed_today_count = await self._habit_log_repository.count_completed_by_user_for_period(
            user_id,
            summary_date,
            summary_date,
            active_only=True,
        )
        remaining_today_count = max(active_habits_count - completed_today_count, 0)
        return DailyProgressSummary(
            active_habits_count=active_habits_count,
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
        total_completions = await self._habit_log_repository.count_completed_by_user_for_period(
            user_id,
            week_start,
            summary_date,
            active_only=True,
        )
        weekly_rate = await self.get_completion_rate(user_id, SEVEN_DAY_WINDOW, summary_date)
        counts_by_habit = await self._habit_log_repository.get_completion_counts_by_habit_for_period(
            user_id,
            week_start,
            summary_date,
            active_only=True,
        )
        streak_snapshots = await self._get_active_habit_streak_snapshots(user_id, summary_date)
        active_habits = await self._habit_repository.get_active_habits_by_user(user_id)

        best_habit_title = None
        best_habit_completion_count = 0
        if counts_by_habit:
            best_habit_id, best_habit_title_candidate, best_habit_count = max(
                counts_by_habit,
                key=lambda item: (item[2], -item[0]),
            )
            if best_habit_count > 0:
                best_habit_title = best_habit_title_candidate
                best_habit_completion_count = best_habit_count

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

        completion_count_map = {
            habit_id: completion_count
            for habit_id, _, completion_count in counts_by_habit
        }
        problem_habits = [
            habit.title
            for habit in active_habits
            if completion_count_map.get(habit.id, 0) == 0
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
        streak_snapshots = await self._get_active_habit_streak_snapshots(user_id, progress_date)
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
        active_habits_count = await self._habit_repository.count_active_habits(user_id)
        completed = await self._habit_log_repository.count_completed_by_user_for_period(
            user_id,
            rate_start_date,
            rate_end_date,
            active_only=True,
        )
        total_possible = active_habits_count * days
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
        habits = await self._habit_repository.get_last_completed_habits_by_user(
            user_id,
            limit=limit,
        )
        return [
            LastCompletedHabit(
                id=habit.id,
                title=habit.title,
                last_completed_at=habit.last_completed_at,
            )
            for habit in habits
            if habit.last_completed_at is not None
        ]

    async def _get_active_habit_streak_snapshots(
        self,
        user_id: int,
        target_date: date,
    ) -> list[HabitStreakSnapshot]:
        active_habits = await self._habit_repository.get_active_habits_by_user(user_id)
        if not active_habits:
            return []

        habit_ids = [habit.id for habit in active_habits]
        completion_rows = await self._habit_log_repository.get_completion_dates_for_habit_ids(habit_ids)
        completion_dates_map: dict[int, list[date]] = defaultdict(list)
        for habit_id, completed_for_date in completion_rows:
            completion_dates_map[habit_id].append(completed_for_date)

        streak_snapshots: list[HabitStreakSnapshot] = []
        for habit in active_habits:
            completion_dates = completion_dates_map.get(habit.id, [])
            completion_date_set = set(completion_dates)
            streak_snapshots.append(
                HabitStreakSnapshot(
                    habit_id=habit.id,
                    title=habit.title,
                    current_streak=self._calculate_current_streak(completion_date_set, target_date),
                    best_streak=self._calculate_best_streak(completion_dates),
                )
            )

        return streak_snapshots

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
    def _get_today() -> date:
        return date.today()
