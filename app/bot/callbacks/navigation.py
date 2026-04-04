from aiogram.filters.callback_data import CallbackData


class OpenTodayCallback(CallbackData, prefix="open_today"):
    pass


class OpenProgressCallback(CallbackData, prefix="open_progress"):
    pass
