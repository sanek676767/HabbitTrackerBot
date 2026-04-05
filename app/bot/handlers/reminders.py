from aiogram import Bot, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.callbacks import (
    HabitReminderCancelCallback,
    HabitReminderDisableCallback,
    HabitReminderMenuCallback,
    HabitReminderSetTimeCallback,
)
from app.bot.keyboards import (
    ALL_MAIN_MENU_BUTTONS,
    get_habit_card_keyboard,
    get_habit_reminder_input_keyboard,
    get_habit_reminder_menu_keyboard,
)
from app.services.habit_service import (
    HabitArchivedError,
    HabitCard,
    HabitDeletedError,
    HabitNotFoundError,
    HabitReminderState,
    HabitReminderValidationError,
    HabitService,
)
from app.services.user_service import UserService, UserTimeValidationError


router = Router(name="reminders")


class HabitReminderStates(StatesGroup):
    waiting_for_current_time = State()
    waiting_for_time = State()


@router.callback_query(HabitReminderMenuCallback.filter())
async def open_reminder_menu(
    callback: CallbackQuery,
    callback_data: HabitReminderMenuCallback,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
        reminder_state = await habit_service.get_habit_reminder_state(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    local_time_status = (
        UserService.format_utc_offset(user.utc_offset_minutes)
        if user.utc_offset_minutes is not None
        else None
    )
    await callback.message.edit_text(
        _build_reminder_menu_text(habit_card, reminder_state, local_time_status),
        reply_markup=get_habit_reminder_menu_keyboard(
            habit_id=habit_card.id,
            source=callback_data.source,
            can_set_time=habit_card.is_active,
            can_disable=reminder_state.enabled,
        ),
    )
    await callback.answer()


@router.callback_query(HabitReminderSetTimeCallback.filter())
async def start_reminder_setup(
    callback: CallbackQuery,
    callback_data: HabitReminderSetTimeCallback,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
        reminder_state = await habit_service.get_habit_reminder_state(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    if not habit_card.is_active:
        await callback.answer("Для архивной привычки напоминание недоступно.", show_alert=True)
        return

    await state.update_data(
        habit_id=habit_card.id,
        source=callback_data.source,
        mode="update" if reminder_state.enabled else "enable",
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
    )

    if user.utc_offset_minutes is None:
        await state.set_state(HabitReminderStates.waiting_for_current_time)
        await callback.message.edit_text(
            _build_current_local_time_prompt_text(habit_card),
            reply_markup=get_habit_reminder_input_keyboard(
                habit_card.id,
                callback_data.source,
            ),
        )
        await callback.answer()
        return

    await state.set_state(HabitReminderStates.waiting_for_time)
    await callback.message.edit_text(
        _build_reminder_time_prompt_text(habit_card, reminder_state),
        reply_markup=get_habit_reminder_input_keyboard(
            habit_card.id,
            callback_data.source,
        ),
    )
    await callback.answer()


@router.callback_query(
    HabitReminderStates.waiting_for_current_time,
    HabitReminderCancelCallback.filter(),
)
@router.callback_query(
    HabitReminderStates.waiting_for_time,
    HabitReminderCancelCallback.filter(),
)
async def cancel_reminder_setup(
    callback: CallbackQuery,
    callback_data: HabitReminderCancelCallback,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        _build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            callback_data.source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
        ),
    )
    await callback.answer("Настройку напоминания отменил.")


@router.callback_query(HabitReminderDisableCallback.filter())
async def disable_reminder(
    callback: CallbackQuery,
    callback_data: HabitReminderDisableCallback,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if callback.from_user is None or callback.message is None:
        await callback.answer()
        return

    user = await user_service.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer("Сначала отправьте /start.", show_alert=True)
        return

    try:
        await habit_service.disable_reminder(user.id, callback_data.habit_id)
        habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await callback.message.edit_text(
        _build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            callback_data.source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
        ),
    )
    await callback.answer("Напоминание выключено.")


@router.message(HabitReminderStates.waiting_for_current_time)
async def save_current_local_time(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await message.answer("Сначала отправьте /start.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Сначала пришли текущее местное время или нажми «⬅️ Отмена».")
        return

    state_data = await state.get_data()
    habit_id = state_data.get("habit_id")
    source = state_data.get("source")
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")

    if (
        not isinstance(habit_id, int)
        or not isinstance(source, str)
        or not isinstance(prompt_chat_id, int)
        or not isinstance(prompt_message_id, int)
    ):
        await state.clear()
        await message.answer("Не получилось продолжить настройку. Открой привычку ещё раз.")
        return

    try:
        await user_service.set_utc_offset_from_local_time(
            user.id,
            message.text or "",
        )
        habit_card = await habit_service.get_habit_card(user.id, habit_id)
        reminder_state = await habit_service.get_habit_reminder_state(user.id, habit_id)
    except UserTimeValidationError as error:
        await message.answer(str(error))
        return
    except HabitNotFoundError:
        await state.clear()
        await message.answer("Привычка не найдена.")
        return
    except HabitDeletedError as error:
        await state.clear()
        await message.answer(str(error))
        return

    if not habit_card.is_active:
        await state.clear()
        await message.answer("Для архивной привычки напоминание недоступно.")
        return

    await state.set_state(HabitReminderStates.waiting_for_time)
    new_prompt_chat_id, new_prompt_message_id = await _render_message(
        bot=message.bot,
        chat_id=prompt_chat_id,
        message_id=prompt_message_id,
        text=_build_reminder_time_prompt_text(habit_card, reminder_state),
        reply_markup=get_habit_reminder_input_keyboard(habit_card.id, source),
    )
    await state.update_data(
        prompt_chat_id=new_prompt_chat_id,
        prompt_message_id=new_prompt_message_id,
    )

    await message.answer("Запомнил местное время. Теперь укажи, когда напоминать.")


@router.message(HabitReminderStates.waiting_for_time)
async def save_reminder_time(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await message.answer("Сначала отправьте /start.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Сначала пришли время напоминания или нажми «⬅️ Отмена».")
        return

    state_data = await state.get_data()
    habit_id = state_data.get("habit_id")
    source = state_data.get("source")
    mode = state_data.get("mode")
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")

    if (
        not isinstance(habit_id, int)
        or not isinstance(source, str)
        or not isinstance(mode, str)
        or not isinstance(prompt_chat_id, int)
        or not isinstance(prompt_message_id, int)
    ):
        await state.clear()
        await message.answer("Не получилось продолжить настройку. Открой привычку ещё раз.")
        return

    try:
        if mode == "update":
            reminder_state = await habit_service.update_reminder_time(
                user.id,
                habit_id,
                message.text or "",
            )
            success_text = f"Теперь напомню в {reminder_state.reminder_time.strftime('%H:%M')}."
        else:
            reminder_state = await habit_service.enable_reminder(
                user.id,
                habit_id,
                message.text or "",
            )
            success_text = f"Буду напоминать в {reminder_state.reminder_time.strftime('%H:%M')}."
        habit_card = await habit_service.get_habit_card(user.id, habit_id)
    except HabitReminderValidationError as error:
        await message.answer(str(error))
        return
    except HabitArchivedError as error:
        await state.clear()
        await message.answer(str(error))
        return
    except HabitNotFoundError:
        await state.clear()
        await message.answer("Привычка не найдена.")
        return
    except HabitDeletedError as error:
        await state.clear()
        await message.answer(str(error))
        return

    await state.clear()
    await _render_message(
        bot=message.bot,
        chat_id=prompt_chat_id,
        message_id=prompt_message_id,
        text=_build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
        ),
    )
    await message.answer(success_text)


def _build_reminder_menu_text(
    habit_card: HabitCard,
    reminder_state: HabitReminderState,
    local_time_status: str | None,
) -> str:
    reminder_time = (
        reminder_state.reminder_time.strftime("%H:%M")
        if reminder_state.enabled and reminder_state.reminder_time is not None
        else "не настроено"
    )

    lines = [
        f"⏰ Напоминание для «{html.quote(habit_card.title)}»",
        "",
        f"Сейчас: {'включено' if reminder_state.enabled else 'выключено'}",
        f"Время: {reminder_time}",
        (
            f"Местное время настроено: {local_time_status}"
            if local_time_status is not None
            else "Местное время ещё не настроено."
        ),
    ]

    if not habit_card.is_active:
        lines.extend(
            [
                "",
                "Для архивной привычки напоминание недоступно.",
            ]
        )
    elif reminder_state.enabled:
        lines.extend(
            [
                "",
                "Можно изменить время или выключить напоминание.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Нажми кнопку ниже, и я помогу включить напоминание.",
            ]
        )

    return "\n".join(lines)


def _build_current_local_time_prompt_text(habit_card: HabitCard) -> str:
    return "\n".join(
        [
            f"⏰ Напоминание для «{html.quote(habit_card.title)}»",
            "",
            "Сначала напиши, сколько у тебя сейчас времени, в формате ЧЧ:ММ.",
            "Например: 21:35",
        ]
    )


def _build_reminder_time_prompt_text(
    habit_card: HabitCard,
    reminder_state: HabitReminderState,
) -> str:
    lines = [
        f"⏰ Напоминание для «{html.quote(habit_card.title)}»",
        "",
        "Теперь напиши время напоминания в формате ЧЧ:ММ.",
        "Например: 09:30",
    ]

    if reminder_state.enabled and reminder_state.reminder_time is not None:
        lines.extend(
            [
                "",
                f"Сейчас стоит: {reminder_state.reminder_time.strftime('%H:%M')}",
            ]
        )

    return "\n".join(lines)


def _build_habit_card_text(habit_card: HabitCard) -> str:
    today_status = "выполнена" if habit_card.is_completed_today else "ещё не выполнена"
    active_status = "активна" if habit_card.is_active else "в архиве"
    reminder_status = (
        habit_card.reminder_time.strftime("%H:%M")
        if habit_card.reminder_enabled and habit_card.reminder_time is not None
        else "выключено"
    )
    return "\n".join(
        [
            f"📌 {html.quote(habit_card.title)}",
            "",
            f"Сегодня: {today_status}",
            f"Текущая серия: {habit_card.current_streak}",
            f"Лучшая серия: {habit_card.best_streak}",
            f"Всего отметок: {habit_card.total_completions}",
            f"Напоминание: {reminder_status}",
            f"Статус: {active_status}",
        ]
    )


async def _render_message(
    bot: Bot,
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
