from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import (
    HabitArchiveCallback,
    HabitDeleteCallback,
    HabitDeleteConfirmCallback,
    HabitDoneCallback,
    HabitEditActionCallback,
    HabitEditCallback,
    HabitGoalActionCallback,
    HabitGoalMenuCallback,
    HabitListCallback,
    HabitListSource,
    HabitReminderCancelCallback,
    HabitReminderDisableCallback,
    HabitReminderMenuCallback,
    HabitReminderSetTimeCallback,
    HabitRestoreCallback,
    HabitStatsCallback,
    HabitViewCallback,
)
from app.services.habit_service import HabitListItem
from app.services.habit_schedule_service import WEEKDAY_BUTTON_LABELS


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
                    text="⬅️ Активные",
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
    is_due_today: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if is_active and is_due_today and not is_completed_today:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Отметить на сегодня",
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
                text="🎯 Цель",
                callback_data=HabitGoalMenuCallback(
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="⏰ Напоминание",
                callback_data=HabitReminderMenuCallback(
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="✏️ Редактировать",
                callback_data=HabitEditCallback(
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            ),
            InlineKeyboardButton(
                text="📊 Статистика",
                callback_data=HabitStatsCallback(
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            ),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="🗂 В архив" if is_active else "♻️ Вернуть в активные",
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
            InlineKeyboardButton(
                text="🗑 Удалить",
                callback_data=HabitDeleteCallback(
                    habit_id=habit_id,
                    source=source,
                ).pack(),
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


def get_habit_delete_confirm_keyboard(habit_id: int, source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, удалить",
                    callback_data=HabitDeleteConfirmCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К привычке",
                    callback_data=HabitViewCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
        ]
    )


def get_habit_stats_keyboard(habit_id: int, source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К привычке",
                    callback_data=HabitViewCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ]
        ]
    )


def get_habit_edit_keyboard(habit_id: int, source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить название",
                    callback_data=HabitEditActionCallback(
                        action="title",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗓 Изменить частоту",
                    callback_data=HabitEditActionCallback(
                        action="frequency",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏰ Изменить напоминание",
                    callback_data=HabitReminderMenuCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🎯 Изменить цель",
                    callback_data=HabitGoalMenuCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К привычке",
                    callback_data=HabitEditActionCallback(
                        action="back",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
        ]
    )


def get_habit_edit_input_keyboard(habit_id: int, source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К привычке",
                    callback_data=HabitEditActionCallback(
                        action="back",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ]
        ]
    )


def get_habit_edit_frequency_keyboard(habit_id: int, source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Каждый день",
                    callback_data=HabitEditActionCallback(
                        action="freq_daily",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Через день",
                    callback_data=HabitEditActionCallback(
                        action="freq_interval",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="По дням недели",
                    callback_data=HabitEditActionCallback(
                        action="freq_weekdays",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=HabitEditActionCallback(
                        action="back",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ],
        ]
    )


def get_habit_edit_weekdays_keyboard(
    selected_days: Sequence[int],
    habit_id: int,
    source: str,
) -> InlineKeyboardMarkup:
    selected_days_set = set(selected_days)
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if index in selected_days_set else ''}{WEEKDAY_BUTTON_LABELS[index]}",
                callback_data=HabitEditActionCallback(
                    action=f"weekday_{index}",
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            )
            for index in range(0, 3)
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if index in selected_days_set else ''}{WEEKDAY_BUTTON_LABELS[index]}",
                callback_data=HabitEditActionCallback(
                    action=f"weekday_{index}",
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            )
            for index in range(3, 6)
        ],
        [
            InlineKeyboardButton(
                text=f"{'✅ ' if 6 in selected_days_set else ''}{WEEKDAY_BUTTON_LABELS[6]}",
                callback_data=HabitEditActionCallback(
                    action="weekday_6",
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Готово",
                callback_data=HabitEditActionCallback(
                    action="weekdays_done",
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅️ К частоте",
                callback_data=HabitEditActionCallback(
                    action="back_frequency",
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_habit_goal_menu_keyboard(
    habit_id: int,
    source: str,
    *,
    has_goal: bool,
) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text="🎯 По выполнениям",
                callback_data=HabitGoalActionCallback(
                    action="completions",
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="🔥 По серии",
                callback_data=HabitGoalActionCallback(
                    action="streak",
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            )
        ],
    ]

    if has_goal:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🗑 Убрать цель",
                    callback_data=HabitGoalActionCallback(
                        action="clear",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К привычке",
                callback_data=HabitGoalActionCallback(
                    action="back",
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_habit_goal_input_keyboard(habit_id: int, source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=HabitGoalActionCallback(
                        action="back_to_menu",
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ]
        ]
    )


def get_habit_reminder_menu_keyboard(
    habit_id: int,
    source: str,
    *,
    can_set_time: bool,
    can_disable: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if can_set_time:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🕒 Изменить время" if can_disable else "🔔 Включить напоминание",
                    callback_data=HabitReminderSetTimeCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ]
        )

    if can_disable:
        rows.append(
            [
                InlineKeyboardButton(
                    text="🔕 Выключить",
                    callback_data=HabitReminderDisableCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К привычке",
                callback_data=HabitViewCallback(
                    habit_id=habit_id,
                    source=source,
                ).pack(),
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_habit_reminder_input_keyboard(habit_id: int, source: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Отмена",
                    callback_data=HabitReminderCancelCallback(
                        habit_id=habit_id,
                        source=source,
                    ).pack(),
                )
            ]
        ]
    )


def get_habit_reminder_notification_keyboard(habit_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Открыть привычку",
                    callback_data=HabitViewCallback(
                        habit_id=habit_id,
                        source=HabitListSource.TODAY.value,
                    ).pack(),
                )
            ]
        ]
    )
