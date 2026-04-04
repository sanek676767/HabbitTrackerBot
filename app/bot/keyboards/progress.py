from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import OpenProgressCallback, OpenTodayCallback


def get_progress_screen_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Сегодня",
                    callback_data=OpenTodayCallback().pack(),
                )
            ]
        ]
    )


def get_summary_actions_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Сегодня",
                    callback_data=OpenTodayCallback().pack(),
                ),
                InlineKeyboardButton(
                    text="📈 Прогресс",
                    callback_data=OpenProgressCallback().pack(),
                ),
            ]
        ]
    )
