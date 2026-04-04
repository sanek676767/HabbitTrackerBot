from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


ADD_HABIT_BUTTON = "➕ Добавить привычку"
MY_HABITS_BUTTON = "📊 Мои привычки"
PROFILE_BUTTON = "👤 Профиль"


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADD_HABIT_BUTTON), KeyboardButton(text=MY_HABITS_BUTTON)],
            [KeyboardButton(text=PROFILE_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )
