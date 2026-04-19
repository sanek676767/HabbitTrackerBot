"""Хелперы возврата между карточкой привычки и меню редактирования."""

from aiogram.types import InlineKeyboardMarkup

from app.bot.callbacks import HabitReturnTarget
from app.bot.habit_text import build_habit_card_text, build_habit_edit_menu_text
from app.bot.keyboards import get_habit_card_keyboard, get_habit_edit_keyboard
from app.services.habit_service import HabitCard


def resolve_habit_return_target(return_to: str | None) -> str:
    if return_to == HabitReturnTarget.EDIT.value:
        return HabitReturnTarget.EDIT.value
    return HabitReturnTarget.CARD.value


def build_habit_return_view(
    habit_card: HabitCard,
    source: str,
    return_to: str | None,
) -> tuple[str, InlineKeyboardMarkup]:
    target = resolve_habit_return_target(return_to)
    if target == HabitReturnTarget.EDIT.value:
        return (
            build_habit_edit_menu_text(habit_card),
            get_habit_edit_keyboard(habit_card.id, source),
        )

    return (
        build_habit_card_text(habit_card),
        get_habit_card_keyboard(
            habit_card.id,
            source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
            is_due_today=habit_card.is_due_today,
        ),
    )
