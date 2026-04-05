from aiogram.filters.callback_data import CallbackData


class AdminDashboardCallback(CallbackData, prefix="admin_dashboard"):
    action: str


class AdminUserCallback(CallbackData, prefix="admin_user"):
    user_id: int


class AdminUserActionCallback(CallbackData, prefix="admin_user_action"):
    action: str
    user_id: int


class AdminFeedbackCallback(CallbackData, prefix="admin_feedback"):
    feedback_id: int


class AdminDeletedHabitActionCallback(CallbackData, prefix="admin_deleted_habit"):
    action: str
    user_id: int
    habit_id: int
