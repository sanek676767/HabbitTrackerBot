from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import CreateHabitCallback
from app.services.habit_schedule_service import WEEKDAY_BUTTON_LABELS


def get_create_habit_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=CreateHabitCallback(action="cancel").pack(),
                )
            ]
        ]
    )


def get_create_habit_frequency_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Каждый день",
                    callback_data=CreateHabitCallback(action="freq_daily").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Через день",
                    callback_data=CreateHabitCallback(action="freq_interval").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="По дням недели",
                    callback_data=CreateHabitCallback(action="freq_weekdays").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=CreateHabitCallback(action="cancel").pack(),
                )
            ],
        ]
    )


def get_create_habit_weekdays_keyboard(selected_days: Sequence[int]) -> InlineKeyboardMarkup:
    selected_days_set = set(selected_days)
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if index in selected_days_set else ''}{WEEKDAY_BUTTON_LABELS[index]}",
                callback_data=CreateHabitCallback(action=f"weekday_{index}").pack(),
            )
            for index in range(0, 3)
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if index in selected_days_set else ''}{WEEKDAY_BUTTON_LABELS[index]}",
                callback_data=CreateHabitCallback(action=f"weekday_{index}").pack(),
            )
            for index in range(3, 6)
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if 6 in selected_days_set else ''}{WEEKDAY_BUTTON_LABELS[6]}",
                callback_data=CreateHabitCallback(action="weekday_6").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Готово",
                callback_data=CreateHabitCallback(action="weekdays_done").pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ К частоте",
                callback_data=CreateHabitCallback(action="to_frequency").pack(),
            ),
            InlineKeyboardButton(
                text="Отмена",
                callback_data=CreateHabitCallback(action="cancel").pack(),
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_create_habit_reminder_keyboard(*, reminder_enabled: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if reminder_enabled:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🕒 Изменить время",
                    callback_data=CreateHabitCallback(action="reminder_setup").pack(),
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔕 Убрать напоминание",
                    callback_data=CreateHabitCallback(action="reminder_clear").pack(),
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Дальше",
                    callback_data=CreateHabitCallback(action="reminder_next").pack(),
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔔 Настроить напоминание",
                    callback_data=CreateHabitCallback(action="reminder_setup").pack(),
                )
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text="Без напоминания",
                    callback_data=CreateHabitCallback(action="reminder_skip").pack(),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К частоте",
                callback_data=CreateHabitCallback(action="to_frequency").pack(),
            ),
            InlineKeyboardButton(
                text="Отмена",
                callback_data=CreateHabitCallback(action="cancel").pack(),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_create_habit_text_input_keyboard(*, back_action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=CreateHabitCallback(action=back_action).pack(),
                ),
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=CreateHabitCallback(action="cancel").pack(),
                ),
            ]
        ]
    )


def get_create_habit_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Создать",
                    callback_data=CreateHabitCallback(action="confirm").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Изменить название",
                    callback_data=CreateHabitCallback(action="edit_title").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗓 Изменить частоту",
                    callback_data=CreateHabitCallback(action="edit_frequency").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏰ Изменить напоминание",
                    callback_data=CreateHabitCallback(action="edit_reminder").pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отмена",
                    callback_data=CreateHabitCallback(action="cancel").pack(),
                )
            ],
        ]
    )
