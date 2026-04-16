from enum import Enum

from aiogram.filters.callback_data import CallbackData


class HabitListSource(str, Enum):
    LIST = "list"
    TODAY = "today"
    ARCHIVE = "archive"


class HabitReturnTarget(str, Enum):
    CARD = "card"
    EDIT = "edit"


class HabitViewCallback(CallbackData, prefix="habit_view"):
    habit_id: int
    source: str


class HabitDoneCallback(CallbackData, prefix="habit_done"):
    habit_id: int
    source: str


class HabitStatsCallback(CallbackData, prefix="habit_stats"):
    habit_id: int
    source: str


class HabitEditCallback(CallbackData, prefix="habit_edit"):
    habit_id: int
    source: str


class HabitEditActionCallback(CallbackData, prefix="habit_edit_action"):
    action: str
    habit_id: int
    source: str


class HabitEditCancelCallback(CallbackData, prefix="habit_edit_cancel"):
    habit_id: int
    source: str


class HabitReminderMenuCallback(CallbackData, prefix="habit_reminder_menu"):
    habit_id: int
    source: str
    return_to: str


class HabitReminderSetTimeCallback(CallbackData, prefix="habit_reminder_set_time"):
    habit_id: int
    source: str
    return_to: str


class HabitReminderDisableCallback(CallbackData, prefix="habit_reminder_disable"):
    habit_id: int
    source: str
    return_to: str


class HabitReminderCancelCallback(CallbackData, prefix="habit_reminder_cancel"):
    habit_id: int
    source: str
    return_to: str


class HabitGoalMenuCallback(CallbackData, prefix="habit_goal_menu"):
    habit_id: int
    source: str
    return_to: str


class HabitGoalActionCallback(CallbackData, prefix="habit_goal_action"):
    action: str
    habit_id: int
    source: str
    return_to: str


class HabitArchiveCallback(CallbackData, prefix="habit_archive"):
    habit_id: int
    source: str


class HabitRestoreCallback(CallbackData, prefix="habit_restore"):
    habit_id: int
    source: str


class HabitDeleteCallback(CallbackData, prefix="habit_delete"):
    habit_id: int
    source: str


class HabitDeleteConfirmCallback(CallbackData, prefix="habit_delete_confirm"):
    habit_id: int
    source: str


class HabitListCallback(CallbackData, prefix="habit_list"):
    source: str
