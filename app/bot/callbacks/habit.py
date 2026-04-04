from enum import Enum

from aiogram.filters.callback_data import CallbackData


class HabitListSource(str, Enum):
    LIST = "list"
    TODAY = "today"
    ARCHIVE = "archive"


class HabitViewCallback(CallbackData, prefix="habit_view"):
    habit_id: int
    source: str


class HabitDoneCallback(CallbackData, prefix="habit_done"):
    habit_id: int
    source: str


class HabitStatsCallback(CallbackData, prefix="habit_stats"):
    habit_id: int
    source: str


class HabitArchiveCallback(CallbackData, prefix="habit_archive"):
    habit_id: int
    source: str


class HabitRestoreCallback(CallbackData, prefix="habit_restore"):
    habit_id: int
    source: str


class HabitListCallback(CallbackData, prefix="habit_list"):
    source: str
