from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


ADD_HABIT_BUTTON = "➕ Добавить привычку"
MY_HABITS_BUTTON = "📋 Мои привычки"
TODAY_BUTTON = "🔥 Сегодня"
PROGRESS_BUTTON = "📈 Прогресс"
PROFILE_BUTTON = "👤 Профиль"
HELP_BUTTON = "❓ Помощь"
FEEDBACK_BUTTON = "💬 Обратная связь"
ADMIN_BUTTON = "🛠 Админка"
BACK_TO_MENU_BUTTON = "⬅️ Назад"

ALL_MAIN_MENU_BUTTONS = {
    ADD_HABIT_BUTTON,
    MY_HABITS_BUTTON,
    TODAY_BUTTON,
    PROGRESS_BUTTON,
    PROFILE_BUTTON,
    HELP_BUTTON,
    FEEDBACK_BUTTON,
    ADMIN_BUTTON,
}


def get_main_menu_keyboard(*, show_admin_button: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text=ADD_HABIT_BUTTON), KeyboardButton(text=MY_HABITS_BUTTON)],
        [KeyboardButton(text=TODAY_BUTTON), KeyboardButton(text=PROGRESS_BUTTON)],
        [KeyboardButton(text=PROFILE_BUTTON), KeyboardButton(text=HELP_BUTTON)],
        [KeyboardButton(text=FEEDBACK_BUTTON)],
    ]
    if show_admin_button:
        keyboard.append([KeyboardButton(text=ADMIN_BUTTON)])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Выбери действие",
    )
