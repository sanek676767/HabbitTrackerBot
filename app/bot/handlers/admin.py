from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

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
from app.bot.keyboards import (
    ADMIN_BUTTON,
    ALL_MAIN_MENU_BUTTONS,
    get_admin_action_log_card_keyboard,
    get_admin_action_log_list_keyboard,
    get_admin_dashboard_keyboard,
    get_admin_feedback_card_keyboard,
    get_admin_feedback_list_keyboard,
    get_admin_feedback_reply_keyboard,
    get_admin_habit_list_keyboard,
    get_admin_restore_confirm_keyboard,
    get_admin_search_keyboard,
    get_admin_user_card_keyboard,
    get_admin_user_confirm_keyboard,
    get_admin_users_keyboard,
)
from app.services.admin_action_log_service import (
    AdminActionLogAccessDeniedError,
    AdminActionLogCard,
    AdminActionLogNotFoundError,
    AdminActionLogPage,
    AdminActionLogService,
)
from app.services.admin_service import (
    AdminAccessDeniedError,
    AdminActionValidationError,
    AdminDashboardData,
    AdminHabitListItem,
    AdminHabitListPage,
    AdminHabitNotFoundError,
    AdminService,
    AdminUserCard,
    AdminUserNotFoundError,
    AdminUsersPage,
)
from app.services.feedback_service import (
    FeedbackAccessDeniedError,
    FeedbackCard,
    FeedbackListPage,
    FeedbackNotFoundError,
    FeedbackService,
    FeedbackValidationError,
)


router = Router(name="admin")

USERS_SECTION = "users"
FEEDBACK_SECTION = "fb"
ACTION_LOG_SECTION = "logs"
GLOBAL_DELETED_SECTION = "gdel"
USER_ACTIVE_SECTION = "uact"
USER_ARCHIVED_SECTION = "uarc"
USER_DELETED_SECTION = "udel"


class AdminStates(StatesGroup):
    waiting_for_user_query = State()
    waiting_for_feedback_reply = State()


@router.message(Command("admin"))
@router.message(F.text == ADMIN_BUTTON)
async def open_admin_dashboard(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
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
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    if callback_data.action == "noop":
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

    await state.clear()
    await callback.message.edit_text(
        _build_dashboard_text(dashboard),
        reply_markup=get_admin_dashboard_keyboard(
            unread_feedback_count=dashboard.unread_feedback_count,
        ),
    )
    await callback.answer()


@router.callback_query(AdminPageCallback.filter())
async def handle_admin_page_callback(
    callback: CallbackQuery,
    callback_data: AdminPageCallback,
    state: FSMContext,
    admin_service: AdminService,
    admin_action_log_service: AdminActionLogService,
    feedback_service: FeedbackService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    try:
        await state.clear()
        await _render_admin_page(
            message=callback.message,
            actor_telegram_id=callback.from_user.id,
            section=callback_data.section,
            page=callback_data.page,
            user_id=callback_data.user_id,
            admin_service=admin_service,
            admin_action_log_service=admin_action_log_service,
            feedback_service=feedback_service,
        )
    except AdminAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except AdminUserNotFoundError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except FeedbackAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except AdminActionLogAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except AdminActionValidationError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await callback.answer()


@router.message(AdminStates.waiting_for_user_query)
async def search_admin_users(
    message: Message,
    state: FSMContext,
    admin_service: AdminService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer(
            "Отправь запрос для поиска или вернись назад кнопкой под сообщением."
        )
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
        await message.answer("Ничего не нашёл. Попробуй идентификатор Telegram, имя пользователя или имя.")
        return

    state_data = await state.get_data()
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")
    await state.clear()

    users_page = AdminUsersPage(
        items=users,
        pagination=_build_single_page_pagination(len(users)),
    )

    if isinstance(prompt_chat_id, int) and isinstance(prompt_message_id, int):
        await _render_message(
            bot=message.bot,
            chat_id=prompt_chat_id,
            message_id=prompt_message_id,
            text=_build_users_list_text(users_page, search_mode=True),
            reply_markup=get_admin_users_keyboard(users_page),
        )
        return

    await message.answer(
        _build_users_list_text(users_page, search_mode=True),
        reply_markup=get_admin_users_keyboard(users_page),
    )


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
        reply_markup=get_admin_user_card_keyboard(user_card),
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
        if callback_data.action == "ask_block":
            user_card = await admin_service.get_user_card(
                callback.from_user.id,
                callback_data.user_id,
            )
            await callback.message.edit_text(
                _build_block_confirmation_text(user_card),
                reply_markup=get_admin_user_confirm_keyboard("block", user_card.id),
            )
            await callback.answer()
            return

        if callback_data.action == "ask_revoke":
            user_card = await admin_service.get_user_card(
                callback.from_user.id,
                callback_data.user_id,
            )
            await callback.message.edit_text(
                _build_revoke_confirmation_text(user_card),
                reply_markup=get_admin_user_confirm_keyboard("revoke", user_card.id),
            )
            await callback.answer()
            return

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
            answer_text = "Пользователь снова активен."
        elif callback_data.action == "grant":
            user_card = await admin_service.grant_admin(
                callback.from_user.id,
                callback_data.user_id,
            )
            answer_text = "Права администратора выданы."
        elif callback_data.action == "revoke":
            user_card = await admin_service.revoke_admin(
                callback.from_user.id,
                callback_data.user_id,
            )
            answer_text = "Права администратора сняты."
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
        reply_markup=get_admin_user_card_keyboard(user_card),
    )
    await callback.answer(answer_text)


@router.callback_query(AdminDeletedHabitActionCallback.filter())
async def handle_admin_deleted_habit_action(
    callback: CallbackQuery,
    callback_data: AdminDeletedHabitActionCallback,
    state: FSMContext,
    admin_service: AdminService,
    admin_action_log_service: AdminActionLogService,
    feedback_service: FeedbackService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    try:
        if callback_data.action == "ask_restore":
            habit = await admin_service.get_deleted_habit(
                callback.from_user.id,
                callback_data.habit_id,
            )
            await callback.message.edit_text(
                _build_restore_confirmation_text(habit),
                reply_markup=get_admin_restore_confirm_keyboard(
                    habit,
                    page=callback_data.page,
                    scope=callback_data.scope,
                ),
            )
            await callback.answer()
            return

        if callback_data.action != "restore":
            await callback.answer()
            return

        restored_habit = await admin_service.restore_deleted_habit(
            callback.from_user.id,
            callback_data.habit_id,
        )
        await state.clear()
        await _render_admin_page(
            message=callback.message,
            actor_telegram_id=callback.from_user.id,
            section=callback_data.scope,
            page=callback_data.page,
            user_id=callback_data.user_id,
            admin_service=admin_service,
            admin_action_log_service=admin_action_log_service,
            feedback_service=feedback_service,
        )
    except AdminAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except (AdminUserNotFoundError, AdminHabitNotFoundError) as error:
        await callback.answer(str(error), show_alert=True)
        return

    await callback.answer(f"Привычка «{restored_habit.title}» восстановлена.")


@router.callback_query(AdminActionLogCallback.filter())
async def open_admin_action_log_card(
    callback: CallbackQuery,
    callback_data: AdminActionLogCallback,
    state: FSMContext,
    admin_action_log_service: AdminActionLogService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    try:
        log_card = await admin_action_log_service.get_log_card(
            callback.from_user.id,
            callback_data.log_id,
        )
    except AdminActionLogAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except AdminActionLogNotFoundError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        _build_action_log_card_text(log_card),
        reply_markup=get_admin_action_log_card_keyboard(
            log_card,
            page=callback_data.page,
        ),
    )
    await callback.answer()


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
        reply_markup=get_admin_feedback_card_keyboard(
            feedback_id=feedback_card.id,
            page=callback_data.page,
            has_reply=feedback_card.admin_reply_text is not None,
        ),
    )
    await callback.answer()


@router.callback_query(AdminFeedbackActionCallback.filter())
async def handle_admin_feedback_action(
    callback: CallbackQuery,
    callback_data: AdminFeedbackActionCallback,
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
            mark_as_read=callback_data.action == "reply",
        )
    except FeedbackAccessDeniedError as error:
        await callback.answer(str(error), show_alert=True)
        return
    except FeedbackNotFoundError as error:
        await callback.answer(str(error), show_alert=True)
        return

    if callback_data.action == "reply":
        await state.set_state(AdminStates.waiting_for_feedback_reply)
        await state.update_data(
            feedback_id=feedback_card.id,
            feedback_page=callback_data.page,
            prompt_chat_id=callback.message.chat.id,
            prompt_message_id=callback.message.message_id,
        )
        await callback.message.edit_text(
            _build_feedback_reply_prompt_text(feedback_card),
            reply_markup=get_admin_feedback_reply_keyboard(
                feedback_id=feedback_card.id,
                page=callback_data.page,
            ),
        )
        await callback.answer()
        return

    await state.clear()
    await callback.message.edit_text(
        _build_feedback_card_text(feedback_card),
        reply_markup=get_admin_feedback_card_keyboard(
            feedback_id=feedback_card.id,
            page=callback_data.page,
            has_reply=feedback_card.admin_reply_text is not None,
        ),
    )
    await callback.answer()


@router.message(AdminStates.waiting_for_feedback_reply)
async def send_admin_feedback_reply(
    message: Message,
    state: FSMContext,
    feedback_service: FeedbackService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Напиши текст ответа или нажми «Отмена» под сообщением.")
        return

    state_data = await state.get_data()
    feedback_id = state_data.get("feedback_id")
    feedback_page = state_data.get("feedback_page")
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")

    if (
        not isinstance(feedback_id, int)
        or not isinstance(feedback_page, int)
        or not isinstance(prompt_chat_id, int)
        or not isinstance(prompt_message_id, int)
    ):
        await state.clear()
        await message.answer("Не получилось продолжить ответ. Открой сообщение ещё раз.")
        return

    try:
        prepared_reply = await feedback_service.prepare_feedback_reply(
            message.from_user.id,
            feedback_id,
            message.text or "",
        )
    except (FeedbackAccessDeniedError, FeedbackNotFoundError, FeedbackValidationError) as error:
        await message.answer(str(error))
        return

    try:
        await message.bot.send_message(
            chat_id=prepared_reply.recipient_telegram_id,
            text=feedback_service.build_admin_reply_message(prepared_reply.reply_text),
        )
    except Exception:
        await message.answer(
            "Не получилось отправить ответ. Возможно, пользователь закрыл диалог с ботом."
        )
        return

    try:
        feedback_card = await feedback_service.save_admin_reply(
            message.from_user.id,
            feedback_id,
            prepared_reply.reply_text,
        )
    except (FeedbackAccessDeniedError, FeedbackNotFoundError, FeedbackValidationError) as error:
        await message.answer(str(error))
        return

    await state.clear()
    await _render_message(
        bot=message.bot,
        chat_id=prompt_chat_id,
        message_id=prompt_message_id,
        text=_build_feedback_card_text(feedback_card),
        reply_markup=get_admin_feedback_card_keyboard(
            feedback_id=feedback_card.id,
            page=feedback_page,
            has_reply=feedback_card.admin_reply_text is not None,
        ),
    )
    await message.answer("Ответ отправлен.")


async def _render_admin_page(
    *,
    message: Message,
    actor_telegram_id: int,
    section: str,
    page: int,
    user_id: int,
    admin_service: AdminService,
    admin_action_log_service: AdminActionLogService,
    feedback_service: FeedbackService,
) -> None:
    if section == USERS_SECTION:
        users_page = await admin_service.list_users_page(actor_telegram_id, page)
        await message.edit_text(
            _build_users_list_text(users_page),
            reply_markup=get_admin_users_keyboard(users_page),
        )
        return

    if section == FEEDBACK_SECTION:
        feedback_page = await feedback_service.get_feedback_page_for_admin(
            actor_telegram_id,
            page=page,
        )
        unread_count = await feedback_service.count_unread_feedback_for_admin(actor_telegram_id)
        await message.edit_text(
            _build_feedback_list_text(feedback_page, unread_count),
            reply_markup=get_admin_feedback_list_keyboard(feedback_page),
        )
        return

    if section == ACTION_LOG_SECTION:
        log_page = await admin_action_log_service.get_logs_page(
            actor_telegram_id,
            page=page,
        )
        await message.edit_text(
            _build_action_logs_list_text(log_page),
            reply_markup=get_admin_action_log_list_keyboard(log_page),
        )
        return

    if section == GLOBAL_DELETED_SECTION:
        habits_page = await admin_service.get_global_deleted_habits_page(
            actor_telegram_id,
            page=page,
        )
        await message.edit_text(
            _build_habit_list_text(habits_page),
            reply_markup=get_admin_habit_list_keyboard(habits_page),
        )
        return

    if section == USER_ACTIVE_SECTION:
        habits_page = await admin_service.get_user_habits_page(
            actor_telegram_id,
            user_id,
            list_type="active",
            page=page,
        )
        await message.edit_text(
            _build_habit_list_text(habits_page),
            reply_markup=get_admin_habit_list_keyboard(habits_page),
        )
        return

    if section == USER_ARCHIVED_SECTION:
        habits_page = await admin_service.get_user_habits_page(
            actor_telegram_id,
            user_id,
            list_type="archived",
            page=page,
        )
        await message.edit_text(
            _build_habit_list_text(habits_page),
            reply_markup=get_admin_habit_list_keyboard(habits_page),
        )
        return

    if section == USER_DELETED_SECTION:
        habits_page = await admin_service.get_user_habits_page(
            actor_telegram_id,
            user_id,
            list_type="deleted",
            page=page,
        )
        await message.edit_text(
            _build_habit_list_text(habits_page),
            reply_markup=get_admin_habit_list_keyboard(habits_page),
        )
        return

    raise AdminActionValidationError("Не удалось открыть этот раздел.")


def _build_dashboard_text(dashboard: AdminDashboardData) -> str:
    return "\n".join(
        [
            "🛠 Админка",
            "",
            f"Пользователей: {dashboard.total_users_count}",
            f"Администраторов: {dashboard.admin_users_count}",
            f"Заблокировано: {dashboard.blocked_users_count}",
            f"Удалённых привычек: {dashboard.deleted_habits_count}",
            f"Новых сообщений: {dashboard.unread_feedback_count}",
            "",
            "Выбери нужный раздел ниже.",
        ]
    )


def _build_search_prompt_text() -> str:
    return "\n".join(
        [
            "🔍 Поиск пользователя",
            "",
            "Отправь идентификатор Telegram, имя пользователя или имя.",
        ]
    )


def _build_users_list_text(users_page: AdminUsersPage, *, search_mode: bool = False) -> str:
    title = "Результаты поиска" if search_mode else "Пользователи"
    return "\n".join(
        [
            f"👥 {title}",
            "",
            f"Показано: {len(users_page.items)}",
            f"Страница: {users_page.pagination.page}/{users_page.pagination.total_pages}",
            "",
            "Выбери пользователя в списке ниже.",
        ]
    )


def _build_user_card_text(user_card: AdminUserCard) -> str:
    username = f"@{user_card.username}" if user_card.username else "не указан"
    full_name = user_card.full_name or "не указано"
    admin_status = "да" if user_card.is_admin else "нет"
    blocked_status = "да" if user_card.is_blocked else "нет"
    created_at = user_card.created_at.strftime("%d.%m.%Y %H:%M")
    last_completed_text = (
        f"{html.quote(user_card.last_completed_habit_title)} — "
        f"{user_card.last_completed_at.strftime('%d.%m.%Y %H:%M')}"
        if user_card.last_completed_habit_title is not None
        and user_card.last_completed_at is not None
        else "пока нет выполнений"
    )
    return "\n".join(
        [
            "👤 Карточка пользователя",
            "",
            f"Внутренний номер: {user_card.id}",
            f"Идентификатор Telegram: {user_card.telegram_id}",
            f"Имя пользователя: {html.quote(username)}",
            f"Имя: {html.quote(full_name)}",
            f"Администратор: {admin_status}",
            f"Заблокирован: {blocked_status}",
            f"В боте с: {created_at}",
            "",
            f"Активных привычек: {user_card.active_habits_count}",
            f"В архиве: {user_card.archived_habits_count}",
            f"Удалено: {user_card.deleted_habits_count}",
            f"Последнее выполнение: {last_completed_text}",
        ]
    )


def _build_habit_list_text(habits_page: AdminHabitListPage) -> str:
    header_map = {
        "active": "🟢 Активные привычки",
        "archived": "🗂 Архив привычек",
        "deleted": "🗑 Удалённые привычки",
        "global_deleted": "🗑 Все удалённые привычки",
    }
    lines = [
        header_map.get(habits_page.list_type, "Привычки"),
        "",
        f"Страница: {habits_page.pagination.page}/{habits_page.pagination.total_pages}",
        f"Всего: {habits_page.pagination.total_items}",
    ]

    if habits_page.list_type != "global_deleted":
        lines.append(f"Пользователь: {html.quote(habits_page.owner_display_name)}")

    if not habits_page.items:
        lines.extend(
            [
                "",
                "Здесь пока пусто.",
            ]
        )
        return "\n".join(lines)

    lines.append("")
    for item in habits_page.items:
        lines.append(_build_habit_line(item, habits_page.list_type))
    return "\n".join(lines)


def _build_feedback_list_text(
    feedback_page: FeedbackListPage,
    unread_count: int,
) -> str:
    return "\n".join(
        [
            "💬 Обратная связь",
            "",
            f"Страница: {feedback_page.page}/{feedback_page.total_pages}",
            f"Всего сообщений: {feedback_page.total_items}",
            f"Новых: {unread_count}",
            "",
            "Выбери сообщение ниже.",
        ]
    )


def _build_action_logs_list_text(log_page: AdminActionLogPage) -> str:
    return "\n".join(
        [
            "📜 Журнал действий",
            "",
            f"Страница: {log_page.pagination.page}/{log_page.pagination.total_pages}",
            f"Всего записей: {log_page.pagination.total_items}",
            "",
            (
                "Выбери запись ниже."
                if log_page.items
                else "Журнал пока пуст."
            ),
        ]
    )


def _build_feedback_card_text(feedback_card: FeedbackCard) -> str:
    username = f"@{feedback_card.username}" if feedback_card.username else "не указан"
    full_name = feedback_card.full_name or "не указано"
    created_at = feedback_card.created_at.strftime("%d.%m.%Y %H:%M")
    status = "прочитано" if feedback_card.is_read else "не прочитано"
    reply_status = (
        feedback_card.admin_replied_at.strftime("%d.%m.%Y %H:%M")
        if feedback_card.admin_replied_at is not None
        else "ответа пока не было"
    )
    lines = [
        "💬 Сообщение",
        "",
        f"Номер сообщения: {feedback_card.id}",
        f"Внутренний номер пользователя: {feedback_card.user_id}",
        f"Идентификатор Telegram: {feedback_card.telegram_id}",
        f"Имя пользователя: {html.quote(username)}",
        f"Имя: {html.quote(full_name)}",
        f"Получено: {created_at}",
        f"Статус: {status}",
        f"Последний ответ: {reply_status}",
        "",
        "Текст:",
        html.quote(feedback_card.message_text),
    ]
    if feedback_card.admin_reply_text is not None:
        lines.extend(
            [
                "",
                "Последний ответ:",
                html.quote(feedback_card.admin_reply_text),
            ]
        )
    return "\n".join(lines)


def _build_action_log_card_text(log_card: AdminActionLogCard) -> str:
    lines = [
        "📜 Запись журнала",
        "",
        f"Номер записи: {log_card.id}",
        f"Администратор: {html.quote(log_card.actor_display_name)}",
        f"Действие: {log_card.action_text}",
        f"Сущность: {html.quote(log_card.entity_text)}",
        (
            f"Целевой пользователь: {html.quote(log_card.target_display_name)}"
            if log_card.target_display_name is not None
            else "Целевой пользователь: не указан"
        ),
        f"Дата и время: {log_card.created_at.strftime('%d.%m.%Y %H:%M')}",
    ]

    if log_card.details:
        lines.extend(["", "Подробности:"])
        for detail in log_card.details:
            lines.append(f"{detail.label}: {html.quote(detail.value)}")

    return "\n".join(lines)


def _build_block_confirmation_text(user_card: AdminUserCard) -> str:
    title = _format_person_title(user_card.username, user_card.full_name, user_card.telegram_id)
    return "\n".join(
        [
            f"🚫 Заблокировать {title}?",
            "",
            "После этого пользователь не сможет пользоваться ботом, пока его не разблокируют.",
        ]
    )


def _build_revoke_confirmation_text(user_card: AdminUserCard) -> str:
    title = _format_person_title(user_card.username, user_card.full_name, user_card.telegram_id)
    return "\n".join(
        [
            f"↩️ Снять права администратора у {title}?",
            "",
            "Доступ к админке пропадёт сразу после подтверждения.",
        ]
    )


def _build_restore_confirmation_text(habit: AdminHabitListItem) -> str:
    owner = f"@{habit.owner_username}" if habit.owner_username else str(habit.owner_telegram_id)
    return "\n".join(
        [
            f"♻️ Восстановить привычку «{html.quote(habit.title)}»?",
            "",
            f"Владелец: {html.quote(owner)}",
            "После восстановления привычка вернётся в архив пользователя.",
        ]
    )


def _build_feedback_reply_prompt_text(feedback_card: FeedbackCard) -> str:
    recipient = (
        f"@{feedback_card.username}"
        if feedback_card.username is not None
        else str(feedback_card.telegram_id)
    )
    return "\n".join(
        [
            "✉️ Ответ пользователю",
            "",
            f"Кому: {html.quote(recipient)}",
            "Напиши ответ одним сообщением.",
        ]
    )


def _build_habit_line(item: AdminHabitListItem, list_type: str) -> str:
    title = html.quote(item.title)
    if list_type == "global_deleted":
        owner = f"@{item.owner_username}" if item.owner_username else str(item.owner_telegram_id)
        deleted_at = item.deleted_at.strftime("%d.%m.%Y %H:%M") if item.deleted_at else "дата не указана"
        return f"• {title} — {html.quote(owner)} — {deleted_at}"

    if list_type == "deleted":
        deleted_at = item.deleted_at.strftime("%d.%m.%Y %H:%M") if item.deleted_at else "дата не указана"
        return f"• {title} — удалена {deleted_at}"

    if item.reminder_enabled and item.reminder_time is not None:
        return f"• {title} — напоминание {item.reminder_time.strftime('%H:%M')}"

    return f"• {title}"


def _format_person_title(
    username: str | None,
    full_name: str | None,
    telegram_id: int,
) -> str:
    if username:
        return f"@{username}"
    if full_name:
        return full_name
    return str(telegram_id)


async def _render_message(
    *,
    bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup,
) -> tuple[int, int]:
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )
        return chat_id, message_id
    except TelegramBadRequest:
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
        )
        return sent_message.chat.id, sent_message.message_id


def _build_single_page_pagination(total_items: int):
    from app.services.admin_service import AdminPagination

    return AdminPagination(
        page=1,
        total_items=total_items,
        total_pages=1,
        has_prev=False,
        has_next=False,
    )
