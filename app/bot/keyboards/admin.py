from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.callbacks import (
    AdminActionLogCallback,
    AdminDashboardCallback,
    AdminDeletedHabitActionCallback,
    AdminFeedbackActionCallback,
    AdminFeedbackCallback,
    AdminPageCallback,
    AdminUserActionCallback,
    AdminUserCallback,
)
from app.services.admin_action_log_service import AdminActionLogCard, AdminActionLogPage
from app.services.admin_service import (
    AdminHabitListItem,
    AdminHabitListPage,
    AdminPagination,
    AdminUserCard,
    AdminUserListItem,
    AdminUsersPage,
)
from app.services.feedback_service import FeedbackListItem, FeedbackListPage


USERS_SECTION = "users"
FEEDBACK_SECTION = "fb"
ACTION_LOG_SECTION = "logs"
GLOBAL_DELETED_SECTION = "gdel"
USER_ACTIVE_SECTION = "uact"
USER_ARCHIVED_SECTION = "uarc"
USER_DELETED_SECTION = "udel"


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
                    text="👥 Пользователи",
                    callback_data=AdminPageCallback(
                        section=USERS_SECTION,
                        page=1,
                        user_id=0,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=feedback_button_text,
                    callback_data=AdminPageCallback(
                        section=FEEDBACK_SECTION,
                        page=1,
                        user_id=0,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="📜 Журнал действий",
                    callback_data=AdminPageCallback(
                        section=ACTION_LOG_SECTION,
                        page=1,
                        user_id=0,
                    ).pack(),
                ),
            ],
        ]
    )


def get_admin_search_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К разделам",
                    callback_data=AdminDashboardCallback(action="home").pack(),
                )
            ]
        ]
    )


def get_admin_users_keyboard(users_page: AdminUsersPage) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for user in users_page.items:
        rows.append(
            [
                InlineKeyboardButton(
                    text=_build_user_button_text(user),
                    callback_data=AdminUserCallback(user_id=user.id).pack(),
                )
            ]
        )

    _append_pagination_row(
        rows,
        pagination=users_page.pagination,
        prev_callback_data=(
            AdminPageCallback(
                section=USERS_SECTION,
                page=users_page.pagination.page - 1,
                user_id=0,
            ).pack()
            if users_page.pagination.has_prev
            else None
        ),
        next_callback_data=(
            AdminPageCallback(
                section=USERS_SECTION,
                page=users_page.pagination.page + 1,
                user_id=0,
            ).pack()
            if users_page.pagination.has_next
            else None
        ),
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К разделам",
                callback_data=AdminDashboardCallback(action="home").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_user_card_keyboard(user_card: AdminUserCard) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🟢 Активные ({user_card.active_habits_count})",
                    callback_data=AdminPageCallback(
                        section=USER_ACTIVE_SECTION,
                        page=1,
                        user_id=user_card.id,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text=f"🗂 Архив ({user_card.archived_habits_count})",
                    callback_data=AdminPageCallback(
                        section=USER_ARCHIVED_SECTION,
                        page=1,
                        user_id=user_card.id,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text=f"🗑 Удалённые ({user_card.deleted_habits_count})",
                    callback_data=AdminPageCallback(
                        section=USER_DELETED_SECTION,
                        page=1,
                        user_id=user_card.id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="✅ Разблокировать" if user_card.is_blocked else "🚫 Заблокировать",
                    callback_data=AdminUserActionCallback(
                        action="unblock" if user_card.is_blocked else "ask_block",
                        user_id=user_card.id,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="↩️ Снять права" if user_card.is_admin else "👑 Выдать права",
                    callback_data=AdminUserActionCallback(
                        action="ask_revoke" if user_card.is_admin else "grant",
                        user_id=user_card.id,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К разделам",
                    callback_data=AdminDashboardCallback(action="home").pack(),
                )
            ],
        ]
    )


def get_admin_user_confirm_keyboard(action: str, user_id: int) -> InlineKeyboardMarkup:
    confirm_text = "Да, продолжить"
    if action == "block":
        confirm_text = "Да, заблокировать"
    elif action == "revoke":
        confirm_text = "Да, снять права"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=confirm_text,
                    callback_data=AdminUserActionCallback(
                        action=action,
                        user_id=user_id,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К карточке",
                    callback_data=AdminUserCallback(user_id=user_id).pack(),
                )
            ],
        ]
    )


def get_admin_habit_list_keyboard(habits_page: AdminHabitListPage) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    section = _get_section_for_habits_page(habits_page)

    if habits_page.list_type in {"deleted", "global_deleted"}:
        for habit in habits_page.items:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"♻️ {_truncate_text(habit.title, 28)}",
                        callback_data=AdminDeletedHabitActionCallback(
                            action="ask_restore",
                            user_id=habit.owner_user_id,
                            habit_id=habit.id,
                            page=habits_page.pagination.page,
                            scope=section,
                        ).pack(),
                    )
                ]
            )

    _append_pagination_row(
        rows,
        pagination=habits_page.pagination,
        prev_callback_data=(
            AdminPageCallback(
                section=section,
                page=habits_page.pagination.page - 1,
                user_id=habits_page.owner_user_id or 0,
            ).pack()
            if habits_page.pagination.has_prev
            else None
        ),
        next_callback_data=(
            AdminPageCallback(
                section=section,
                page=habits_page.pagination.page + 1,
                user_id=habits_page.owner_user_id or 0,
            ).pack()
            if habits_page.pagination.has_next
            else None
        ),
    )

    if habits_page.list_type == "global_deleted":
        rows.append(
            [
                InlineKeyboardButton(
                    text="⬅️ К разделам",
                    callback_data=AdminDashboardCallback(action="home").pack(),
                )
            ]
        )
    else:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⬅️ К карточке",
                    callback_data=AdminUserCallback(user_id=habits_page.owner_user_id or 0).pack(),
                )
            ]
        )

    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_restore_confirm_keyboard(
    habit: AdminHabitListItem,
    *,
    page: int,
    scope: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Да, восстановить",
                    callback_data=AdminDeletedHabitActionCallback(
                        action="restore",
                        user_id=habit.owner_user_id,
                        habit_id=habit.id,
                        page=page,
                        scope=scope,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад",
                    callback_data=AdminPageCallback(
                        section=scope,
                        page=page,
                        user_id=habit.owner_user_id,
                    ).pack(),
                )
            ],
        ]
    )


def get_admin_feedback_list_keyboard(feedback_page: FeedbackListPage) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for feedback in feedback_page.items:
        rows.append(
            [
                InlineKeyboardButton(
                    text=_build_feedback_button_text(feedback),
                    callback_data=AdminFeedbackCallback(
                        feedback_id=feedback.id,
                        page=feedback_page.page,
                    ).pack(),
                )
            ]
        )

    _append_pagination_row(
        rows,
        pagination=_to_admin_pagination(feedback_page),
        prev_callback_data=(
            AdminPageCallback(
                section=FEEDBACK_SECTION,
                page=feedback_page.page - 1,
                user_id=0,
            ).pack()
            if feedback_page.has_prev
            else None
        ),
        next_callback_data=(
            AdminPageCallback(
                section=FEEDBACK_SECTION,
                page=feedback_page.page + 1,
                user_id=0,
            ).pack()
            if feedback_page.has_next
            else None
        ),
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К разделам",
                callback_data=AdminDashboardCallback(action="home").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_feedback_card_keyboard(
    *,
    feedback_id: int,
    page: int,
    has_reply: bool,
) -> InlineKeyboardMarkup:
    reply_button_text = "✉️ Ответить ещё раз" if has_reply else "✉️ Ответить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=reply_button_text,
                    callback_data=AdminFeedbackActionCallback(
                        action="reply",
                        feedback_id=feedback_id,
                        page=page,
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К сообщениям",
                    callback_data=AdminPageCallback(
                        section=FEEDBACK_SECTION,
                        page=page,
                        user_id=0,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="⬅️ К разделам",
                    callback_data=AdminDashboardCallback(action="home").pack(),
                ),
            ],
        ]
    )


def get_admin_feedback_reply_keyboard(*, feedback_id: int, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ Отмена",
                    callback_data=AdminFeedbackActionCallback(
                        action="cancel",
                        feedback_id=feedback_id,
                        page=page,
                    ).pack(),
                )
            ]
        ]
    )


def get_admin_action_log_list_keyboard(log_page: AdminActionLogPage) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in log_page.items:
        rows.append(
            [
                InlineKeyboardButton(
                    text=item.summary_text,
                    callback_data=AdminActionLogCallback(
                        log_id=item.id,
                        page=log_page.pagination.page,
                    ).pack(),
                )
            ]
        )

    _append_pagination_row(
        rows,
        pagination=log_page.pagination,
        prev_callback_data=(
            AdminPageCallback(
                section=ACTION_LOG_SECTION,
                page=log_page.pagination.page - 1,
                user_id=0,
            ).pack()
            if log_page.pagination.has_prev
            else None
        ),
        next_callback_data=(
            AdminPageCallback(
                section=ACTION_LOG_SECTION,
                page=log_page.pagination.page + 1,
                user_id=0,
            ).pack()
            if log_page.pagination.has_next
            else None
        ),
    )
    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К разделам",
                callback_data=AdminDashboardCallback(action="home").pack(),
            )
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_admin_action_log_card_keyboard(
    log_card: AdminActionLogCard,
    *,
    page: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ К журналу",
                    callback_data=AdminPageCallback(
                        section=ACTION_LOG_SECTION,
                        page=page,
                        user_id=0,
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="⬅️ К разделам",
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

    if status_parts:
        return f"{title} {' '.join(status_parts)}"
    return title


def _build_feedback_button_text(feedback: FeedbackListItem) -> str:
    author = feedback.username or feedback.full_name or str(feedback.telegram_id)
    if feedback.username and not feedback.username.startswith("@"):
        author = f"@{feedback.username}"

    if not feedback.is_read:
        prefix = "🆕"
    elif feedback.has_reply:
        prefix = "✉️"
    else:
        prefix = "💬"

    created_at = feedback.created_at.strftime("%d.%m %H:%M")
    return f"{prefix} {author} • {created_at} • {feedback.preview_text}"


def _append_pagination_row(
    rows: list[list[InlineKeyboardButton]],
    *,
    pagination: AdminPagination,
    prev_callback_data: str | None,
    next_callback_data: str | None,
) -> None:
    if not pagination.has_prev and not pagination.has_next:
        return

    row: list[InlineKeyboardButton] = []
    if prev_callback_data is not None:
        row.append(
            InlineKeyboardButton(
                text="⬅️",
                callback_data=prev_callback_data,
            )
        )
    row.append(
        InlineKeyboardButton(
            text=f"{pagination.page}/{pagination.total_pages}",
            callback_data=AdminDashboardCallback(action="noop").pack(),
        )
    )
    if next_callback_data is not None:
        row.append(
            InlineKeyboardButton(
                text="➡️",
                callback_data=next_callback_data,
            )
        )
    rows.append(row)


def _to_admin_pagination(feedback_page: FeedbackListPage) -> AdminPagination:
    return AdminPagination(
        page=feedback_page.page,
        total_items=feedback_page.total_items,
        total_pages=feedback_page.total_pages,
        has_prev=feedback_page.has_prev,
        has_next=feedback_page.has_next,
    )


def _get_section_for_habits_page(habits_page: AdminHabitListPage) -> str:
    if habits_page.list_type == "active":
        return USER_ACTIVE_SECTION
    if habits_page.list_type == "archived":
        return USER_ARCHIVED_SECTION
    if habits_page.list_type == "deleted":
        return USER_DELETED_SECTION
    return GLOBAL_DELETED_SECTION


def _truncate_text(value: str, max_length: int) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 1]}…"
