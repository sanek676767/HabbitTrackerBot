from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import FeedbackCallback


def get_feedback_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Отмена",
                    callback_data=FeedbackCallback(action="cancel").pack(),
                )
            ]
        ]
    )
