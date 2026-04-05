from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import (
    AdminDashboardCallback,
    AdminDeletedHabitActionCallback,
    AdminFeedbackCallback,
    AdminUserActionCallback,
    AdminUserCallback,
)
from app.services.admin_service import AdminUserListItem, DeletedHabitListItem
from app.services.feedback_service import FeedbackListItem


def get_admin_dashboard_keyboard(*, unread_feedback_count: int) -> InlineKeyboardMarkup:
    feedback_button_text = "💬 Обратная связь"
    if unread_feedback_count > 0:
        feedback_button_text = f"💬 Обратная связь ({unread_feedback_count})"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔍 Найти пользователя",
                    callback_data=AdminDashboardCallback(action="search").pack(),
                ),
                InlineKeyboardButton(
                    text="👥 Все пользователи",
                    callback_data=AdminDashboardCallback(action="list_users").pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=feedback_button_text,
                    callback_data=AdminDashboardCallback(action="feedback").pack(),
                )
            ],
        ]
    )


def get_admin_search_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Dashboard",
                    callback_data=AdminDashboardCallback(action="home").pack(),
                )
            ]
        ]
    )


def get_admin_users_keyboard(users: Sequence[AdminUserListItem]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for user in users:
        rows.append(
            [
                InlineKeyboardButton(
                    text=_build_user_button_text(user),
                    callback_data=AdminUserCallback(user_id=user.id).pack(),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Dashboard",
                callback_data=AdminDashboardCallback(action="home").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_user_card_keyboard(
    user_id: int,
    *,
    is_admin: bool,
    is_blocked: bool,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Разблокировать" if is_blocked else "🚫 Заблокировать",
                    callback_data=AdminUserActionCallback(
                        action="unblock" if is_blocked else "block",
                        user_id=user_id,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="↩️ Снять admin" if is_admin else "👑 Выдать admin",
                    callback_data=AdminUserActionCallback(
                        action="revoke_admin" if is_admin else "grant_admin",
                        user_id=user_id,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Soft-deleted habits",
                    callback_data=AdminUserActionCallback(
                        action="deleted_habits",
                        user_id=user_id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Dashboard",
                    callback_data=AdminDashboardCallback(action="home").pack(),
                )
            ],
        ]
    )


def get_admin_deleted_habits_keyboard(
    user_id: int,
    habits: Sequence[DeletedHabitListItem],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for habit in habits:
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"♻️ {habit.title}",
                    callback_data=AdminDeletedHabitActionCallback(
                        action="restore",
                        user_id=user_id,
                        habit_id=habit.id,
                    ).pack(),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К пользователю",
                callback_data=AdminUserCallback(user_id=user_id).pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_feedback_list_keyboard(feedback_items: Sequence[FeedbackListItem]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for feedback in feedback_items:
        rows.append(
            [
                InlineKeyboardButton(
                    text=_build_feedback_button_text(feedback),
                    callback_data=AdminFeedbackCallback(feedback_id=feedback.id).pack(),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ Dashboard",
                callback_data=AdminDashboardCallback(action="home").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_feedback_card_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К feedback",
                    callback_data=AdminDashboardCallback(action="feedback").pack(),
                ),
                InlineKeyboardButton(
                    text="⬅️ Dashboard",
                    callback_data=AdminDashboardCallback(action="home").pack(),
                ),
            ]
        ]
    )


def _build_user_button_text(user: AdminUserListItem) -> str:
    title = user.username or user.full_name or str(user.telegram_id)
    if user.username and not user.username.startswith("@"):
        title = f"@{user.username}"

    status_parts: list[str] = []
    if user.is_admin:
        status_parts.append("👑")
    if user.is_blocked:
        status_parts.append("🚫")

    status_suffix = f" {' '.join(status_parts)}" if status_parts else ""
    return f"{title}{status_suffix}"


def _build_feedback_button_text(feedback: FeedbackListItem) -> str:
    author = feedback.username or feedback.full_name or str(feedback.telegram_id)
    if feedback.username and not feedback.username.startswith("@"):
        author = f"@{feedback.username}"

    unread_prefix = "🆕 " if not feedback.is_read else ""
    created_at = feedback.created_at.strftime("%d.%m %H:%M")
    return f"{unread_prefix}{author} • {created_at} • {feedback.preview_text}"
