from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import (
    HabitArchiveCallback,
    HabitDoneCallback,
    HabitListCallback,
    HabitListSource,
    HabitRestoreCallback,
    HabitStatsCallback,
    HabitViewCallback,
)
from app.services.habit_service import HabitListItem


def get_habits_list_keyboard(
    habits: Sequence[HabitListItem],
    source: str,
    *,
    show_completion_status: bool = False,
    show_archive_switch: bool = False,
    show_back_to_active: bool = False,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for habit in habits:
        button_text = habit.title
        if show_completion_status:
            status_icon = "✅" if habit.is_completed_today else "⬜"
            button_text = f"{status_icon} {habit.title}"

        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=HabitViewCallback(
                        habit_id=habit.id,
                        source=source,
                    ).pack(),
                )
            ]
        )

    if show_archive_switch:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🗂 Архив",
                    callback_data=HabitListCallback(source=HabitListSource.ARCHIVE.value).pack(),
                )
            ]
        )

    if show_back_to_active:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⬅️ Активные привычки",
                    callback_data=HabitListCallback(source=HabitListSource.LIST.value).pack(),
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_habit_card_keyboard(
    habit_id: int,
    source: str,
    *,
    is_completed_today: bool,
    is_active: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if is_active and not is_completed_today:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Отметить сегодня",
                    callback_data=HabitDoneCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="📈 Статистика",
                callback_data=HabitStatsCallback(
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="⏸ Архивировать" if is_active else "♻️ Вернуть в активные",
                callback_data=(
                    HabitArchiveCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack()
                    if is_active
                    else HabitRestoreCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack()
                ),
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=HabitListCallback(source=source).pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_habit_stats_keyboard(habit_id: int, source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к привычке",
                    callback_data=HabitViewCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ]
        ]
    )
