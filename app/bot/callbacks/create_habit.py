from aiogram.filters.callback_data import CallbackData


class CreateHabitCallback(CallbackData, prefix="create_habit"):
    action: str
