from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from app.bot.callbacks import CreateHabitCallback


ADD_HABIT_BUTTON = "➕ Добавить привычку"
MY_HABITS_BUTTON = "📋 Мои привычки"
TODAY_BUTTON = "🔥 Сегодня"
PROFILE_BUTTON = "👤 Профиль"
BACK_TO_MENU_BUTTON = "⬅️ Назад"
ALL_MAIN_MENU_BUTTONS = {
    ADD_HABIT_BUTTON,
    MY_HABITS_BUTTON,
    TODAY_BUTTON,
    PROFILE_BUTTON,
}


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=ADD_HABIT_BUTTON), KeyboardButton(text=MY_HABITS_BUTTON)],
            [KeyboardButton(text=TODAY_BUTTON), KeyboardButton(text=PROFILE_BUTTON)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )


def get_create_habit_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=BACK_TO_MENU_BUTTON,
                    callback_data=CreateHabitCallback(action="cancel").pack(),
                )
            ]
        ]
    )
