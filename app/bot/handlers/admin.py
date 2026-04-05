from aiogram import Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import (
    AdminDashboardCallback,
    AdminDeletedHabitActionCallback,
    AdminFeedbackCallback,
    AdminUserActionCallback,
    AdminUserCallback,
)
from app.bot.keyboards import (
    ALL_MAIN_MENU_BUTTONS,
    get_admin_dashboard_keyboard,
    get_admin_deleted_habits_keyboard,
    get_admin_feedback_card_keyboard,
    get_admin_feedback_list_keyboard,
    get_admin_search_keyboard,
    get_admin_user_card_keyboard,
    get_admin_users_keyboard,
)
from app.services.admin_service import (
    AdminAccessDeniedError,
    AdminActionValidationError,
    AdminDashboardData,
    AdminHabitNotFoundError,
    AdminService,
    AdminUserCard,
    AdminUserListItem,
    AdminUserNotFoundError,
    DeletedHabitListItem,
)
from app.services.feedback_service import (
    FeedbackAccessDeniedError,
    FeedbackCard,
    FeedbackListItem,
    FeedbackNotFoundError,
    FeedbackService,
)


router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_for_user_query = State()


@router.message(Command("admin"))
async def open_admin_dashboard(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    try:
        dashboard = await admin_service.get_dashboard(message.from_user.id)
    except AdminAccessDeniedError as error:
        await message.answer(str(error))
        return

    await state.clear()
    await message.answer(
        _build_dashboard_text(dashboard),
        reply_markup=get_admin_dashboard_keyboard(
            unread_feedback_count=dashboard.unread_feedback_count,
        ),
    )


@router.callback_query(AdminDashboardCallback.filter())
async def handle_admin_dashboard_callback(
    callback: CallbackQuery,
    callback_data: AdminDashboardCallback,
    state: FSMContext,
    admin_service: AdminService,
    feedback_service: FeedbackService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    try:
        dashboard = await admin_service.get_dashboard(callback.from_user.id)
    except AdminAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    if callback_data.action == "search":
        await state.set_state(AdminStates.waiting_for_user_query)
        await state.update_data(
            prompt_chat_id=callback.message.chat.id,
            prompt_message_id=callback.message.message_id,
        )
        await callback.message.edit_text(
            _build_search_prompt_text(),
            reply_markup=get_admin_search_keyboard(),
        )
        await callback.answer()
        return

    if callback_data.action == "list_users":
        await state.clear()
        users = await admin_service.list_users(callback.from_user.id)
        await callback.message.edit_text(
            _build_users_list_text(users),
            reply_markup=get_admin_users_keyboard(users),
        )
        await callback.answer()
        return

    if callback_data.action == "feedback":
        await state.clear()
        try:
            feedback_items = await feedback_service.get_feedback_list_for_admin(
                callback.from_user.id,
            )
            unread_count = await feedback_service.count_unread_feedback_for_admin(
                callback.from_user.id,
            )
        except FeedbackAccessDeniedError as error:
            await callback.answer(str(error), show_alert=True)
            return

        await callback.message.edit_text(
            _build_feedback_list_text(feedback_items, unread_count),
            reply_markup=get_admin_feedback_list_keyboard(feedback_items),
        )
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text(
        _build_dashboard_text(dashboard),
        reply_markup=get_admin_dashboard_keyboard(
            unread_feedback_count=dashboard.unread_feedback_count,
        ),
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_user_query)
async def search_admin_users(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Нажми «Dashboard» под сообщением или отправь поисковый запрос.")
        return

    try:
        users = await admin_service.search_users(
            message.from_user.id,
            message.text or "",
        )
    except AdminAccessDeniedError as error:
        await state.clear()
        await message.answer(str(error))
        return

    if not users:
        await message.answer("Ничего не нашёл. Попробуй Telegram ID, username или имя.")
        return

    state_data = await state.get_data()
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")
    await state.clear()

    if isinstance(prompt_chat_id, int) and isinstance(prompt_message_id, int):
        try:
            await message.bot.edit_message_text(
                chat_id=prompt_chat_id,
                message_id=prompt_message_id,
                text=_build_users_list_text(users),
                reply_markup=get_admin_users_keyboard(users),
            )
        except TelegramBadRequest:
            await message.answer(
                _build_users_list_text(users),
                reply_markup=get_admin_users_keyboard(users),
            )
    else:
        await message.answer(
            _build_users_list_text(users),
            reply_markup=get_admin_users_keyboard(users),
        )

    await message.answer("Поиск готов. Открой нужную карточку пользователя.")


@router.callback_query(AdminUserCallback.filter())
async def open_admin_user_card(
    callback: CallbackQuery,
    callback_data: AdminUserCallback,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    try:
        user_card = await admin_service.get_user_card(
            callback.from_user.id,
            callback_data.user_id,
        )
    except AdminAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except AdminUserNotFoundError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        _build_user_card_text(user_card),
        reply_markup=get_admin_user_card_keyboard(
            user_card.id,
            is_admin=user_card.is_admin,
            is_blocked=user_card.is_blocked,
        ),
    )
    await callback.answer()


@router.callback_query(AdminUserActionCallback.filter())
async def handle_admin_user_action(
    callback: CallbackQuery,
    callback_data: AdminUserActionCallback,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    try:
        if callback_data.action == "block":
            user_card = await admin_service.block_user(
                callback.from_user.id,
                callback_data.user_id,
            )
            answer_text = "Пользователь заблокирован."
        elif callback_data.action == "unblock":
            user_card = await admin_service.unblock_user(
                callback.from_user.id,
                callback_data.user_id,
            )
            answer_text = "Пользователь разблокирован."
        elif callback_data.action == "grant_admin":
            user_card = await admin_service.grant_admin(
                callback.from_user.id,
                callback_data.user_id,
            )
            answer_text = "Права admin выданы."
        elif callback_data.action == "revoke_admin":
            user_card = await admin_service.revoke_admin(
                callback.from_user.id,
                callback_data.user_id,
            )
            answer_text = "Права admin сняты."
        elif callback_data.action == "deleted_habits":
            user_card = await admin_service.get_user_card(
                callback.from_user.id,
                callback_data.user_id,
            )
            deleted_habits = await admin_service.get_deleted_habits(
                callback.from_user.id,
                callback_data.user_id,
            )
            await state.clear()
            await callback.message.edit_text(
                _build_deleted_habits_text(user_card, deleted_habits),
                reply_markup=get_admin_deleted_habits_keyboard(
                    callback_data.user_id,
                    deleted_habits,
                ),
            )
            await callback.answer()
            return
        else:
            await callback.answer()
            return
    except AdminAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except AdminUserNotFoundError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except AdminActionValidationError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        _build_user_card_text(user_card),
        reply_markup=get_admin_user_card_keyboard(
            user_card.id,
            is_admin=user_card.is_admin,
            is_blocked=user_card.is_blocked,
        ),
    )
    await callback.answer(answer_text)


@router.callback_query(AdminDeletedHabitActionCallback.filter())
async def handle_admin_deleted_habit_action(
    callback: CallbackQuery,
    callback_data: AdminDeletedHabitActionCallback,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    try:
        if callback_data.action == "restore":
            restored_habit = await admin_service.restore_deleted_habit(
                callback.from_user.id,
                callback_data.habit_id,
            )
            user_card = await admin_service.get_user_card(
                callback.from_user.id,
                callback_data.user_id,
            )
            deleted_habits = await admin_service.get_deleted_habits(
                callback.from_user.id,
                callback_data.user_id,
            )
        else:
            await callback.answer()
            return
    except AdminAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except (AdminUserNotFoundError, AdminHabitNotFoundError) as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        _build_deleted_habits_text(user_card, deleted_habits),
        reply_markup=get_admin_deleted_habits_keyboard(
            callback_data.user_id,
            deleted_habits,
        ),
    )
    await callback.answer(
        f"Привычка «{restored_habit.title}» восстановлена в архив."
    )


@router.callback_query(AdminFeedbackCallback.filter())
async def open_admin_feedback_card(
    callback: CallbackQuery,
    callback_data: AdminFeedbackCallback,
    state: FSMContext,
    feedback_service: FeedbackService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    try:
        feedback_card = await feedback_service.get_feedback_card_for_admin(
            callback.from_user.id,
            callback_data.feedback_id,
            mark_as_read=True,
        )
    except FeedbackAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except FeedbackNotFoundError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        _build_feedback_card_text(feedback_card),
        reply_markup=get_admin_feedback_card_keyboard(),
    )
    await callback.answer("Сообщение открыто.")


def _build_dashboard_text(dashboard: AdminDashboardData) -> str:
    return "\n".join(
        [
            "🛠 Admin panel",
            "",
            f"Пользователей: {dashboard.total_users_count}",
            f"Админов: {dashboard.admin_users_count}",
            f"Заблокировано: {dashboard.blocked_users_count}",
            f"Soft-deleted habits: {dashboard.deleted_habits_count}",
            f"Unread feedback: {dashboard.unread_feedback_count}",
            "",
            "Открой нужный раздел ниже.",
        ]
    )


def _build_search_prompt_text() -> str:
    return "\n".join(
        [
            "🔍 Поиск пользователя",
            "",
            "Отправь Telegram ID, username или имя.",
            "Можно искать по части строки.",
        ]
    )


def _build_users_list_text(users: list[AdminUserListItem]) -> str:
    return "\n".join(
        [
            "👥 Пользователи",
            "",
            f"Найдено: {len(users)}",
            "Выбери пользователя ниже.",
        ]
    )


def _build_user_card_text(user_card: AdminUserCard) -> str:
    username = f"@{user_card.username}" if user_card.username else "не указан"
    full_name = user_card.full_name or "не указано"
    admin_status = "Да" if user_card.is_admin else "Нет"
    blocked_status = "Да" if user_card.is_blocked else "Нет"
    created_at = user_card.created_at.strftime("%d.%m.%Y %H:%M UTC")
    last_completed_text = (
        f"{html.quote(user_card.last_completed_habit_title)} - "
        f"{user_card.last_completed_at.strftime('%d.%m.%Y %H:%M UTC')}"
        if user_card.last_completed_habit_title is not None
        and user_card.last_completed_at is not None
        else "нет выполнений"
    )
    return "\n".join(
        [
            "👤 User card",
            "",
            f"User ID: {user_card.id}",
            f"Telegram ID: {user_card.telegram_id}",
            f"Username: {html.quote(username)}",
            f"Имя: {html.quote(full_name)}",
            f"Admin: {admin_status}",
            f"Blocked: {blocked_status}",
            f"В боте с: {created_at}",
            "",
            f"Активных привычек: {user_card.active_habits_count}",
            f"Архивных привычек: {user_card.archived_habits_count}",
            f"Soft-deleted habits: {user_card.deleted_habits_count}",
            f"Последняя активность: {last_completed_text}",
        ]
    )


def _build_deleted_habits_text(
    user_card: AdminUserCard,
    habits: list[DeletedHabitListItem],
) -> str:
    lines = [
        f"🗑 Soft-deleted habits пользователя {user_card.telegram_id}",
        "",
        f"Всего удалённых: {len(habits)}",
    ]

    if not habits:
        lines.extend(
            [
                "",
                "У пользователя сейчас нет soft-deleted habits.",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "",
            "Список:",
        ]
    )
    for habit in habits:
        deleted_at = (
            habit.deleted_at.strftime("%d.%m.%Y %H:%M UTC")
            if habit.deleted_at is not None
            else "дата не сохранена"
        )
        lines.append(f"• {html.quote(habit.title)} ({deleted_at})")

    return "\n".join(lines)


def _build_feedback_list_text(
    feedback_items: list[FeedbackListItem],
    unread_count: int,
) -> str:
    return "\n".join(
        [
            "💬 Обратная связь",
            "",
            f"Всего сообщений в списке: {len(feedback_items)}",
            f"Непрочитанных: {unread_count}",
            "",
            "Выбери сообщение ниже.",
        ]
    )


def _build_feedback_card_text(feedback_card: FeedbackCard) -> str:
    username = f"@{feedback_card.username}" if feedback_card.username else "не указан"
    full_name = feedback_card.full_name or "не указано"
    created_at = feedback_card.created_at.strftime("%d.%m.%Y %H:%M UTC")
    status = "прочитано" if feedback_card.is_read else "не прочитано"
    return "\n".join(
        [
            "💬 Feedback card",
            "",
            f"Feedback ID: {feedback_card.id}",
            f"User ID: {feedback_card.user_id}",
            f"Telegram ID: {feedback_card.telegram_id}",
            f"Username: {html.quote(username)}",
            f"Имя: {html.quote(full_name)}",
            f"Дата: {created_at}",
            f"Статус: {status}",
            "",
            "Текст:",
            html.quote(feedback_card.message_text),
        ]
    )
