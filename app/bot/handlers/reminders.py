from aiogram import Bot, F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.bot.callbacks import (
    HabitReminderCancelCallback,
    HabitReminderDisableCallback,
    HabitReminderMenuCallback,
    HabitReminderSetTimeCallback,
    HabitReturnTarget,
)
from app.bot.habit_navigation import build_habit_return_view
from app.bot.keyboards import (
    ALL_MAIN_MENU_BUTTONS,
    get_habit_reminder_input_keyboard,
    get_habit_reminder_menu_keyboard,
)
from app.services.habit_service import (
    HabitArchivedError,
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


@router.callback_query(F.data.regexp(r"^habit_reminder_menu:\d+:[^:]+$"))
async def open_reminder_menu_legacy(
    callback: CallbackQuery,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    callback_data = _parse_legacy_reminder_menu_callback(callback.data)
    if callback_data is None:
        await callback.answer()
        return

    await open_reminder_menu(callback, callback_data, user_service, habit_service)


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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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
        _build_reminder_menu_text(
            habit_card.title,
            habit_card.frequency_text,
            reminder_state,
            local_time_status,
            habit_card.is_active,
        ),
        reply_markup=get_habit_reminder_menu_keyboard(
            habit_id=habit_card.id,
            source=callback_data.source,
            can_set_time=habit_card.is_active,
            can_disable=reminder_state.enabled,
            return_to=callback_data.return_to,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^habit_reminder_set_time:\d+:[^:]+$"))
async def start_reminder_setup_legacy(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    callback_data = _parse_legacy_reminder_action_callback(
        callback.data,
        prefix="habit_reminder_set_time",
        callback_factory=HabitReminderSetTimeCallback,
    )
    if callback_data is None:
        await callback.answer()
        return

    await start_reminder_setup(callback, callback_data, state, user_service, habit_service)


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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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
        return_to=callback_data.return_to,
        mode="update" if reminder_state.enabled else "enable",
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
    )

    if user.utc_offset_minutes is None:
        await state.set_state(HabitReminderStates.waiting_for_current_time)
        await callback.message.edit_text(
            _build_current_local_time_prompt_text(habit_card.title),
            reply_markup=get_habit_reminder_input_keyboard(
                habit_card.id,
                callback_data.source,
                callback_data.return_to,
            ),
        )
        await callback.answer()
        return

    await state.set_state(HabitReminderStates.waiting_for_time)
    await callback.message.edit_text(
        _build_reminder_time_prompt_text(habit_card.title, reminder_state),
        reply_markup=get_habit_reminder_input_keyboard(
            habit_card.id,
            callback_data.source,
            callback_data.return_to,
        ),
    )
    await callback.answer()


@router.callback_query(
    HabitReminderStates.waiting_for_current_time,
    F.data.regexp(r"^habit_reminder_cancel:\d+:[^:]+$"),
)
@router.callback_query(
    HabitReminderStates.waiting_for_time,
    F.data.regexp(r"^habit_reminder_cancel:\d+:[^:]+$"),
)
async def cancel_reminder_setup_legacy(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    callback_data = _parse_legacy_reminder_action_callback(
        callback.data,
        prefix="habit_reminder_cancel",
        callback_factory=HabitReminderCancelCallback,
    )
    if callback_data is None:
        await callback.answer()
        return

    await cancel_reminder_setup(callback, callback_data, state, user_service, habit_service)


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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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
    text, reply_markup = build_habit_return_view(
        habit_card,
        callback_data.source,
        callback_data.return_to,
    )
    await callback.message.edit_text(text, reply_markup=reply_markup)
    await callback.answer("Настройку напоминания отменил.")


@router.callback_query(F.data.regexp(r"^habit_reminder_disable:\d+:[^:]+$"))
async def disable_reminder_legacy(
    callback: CallbackQuery,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    callback_data = _parse_legacy_reminder_action_callback(
        callback.data,
        prefix="habit_reminder_disable",
        callback_factory=HabitReminderDisableCallback,
    )
    if callback_data is None:
        await callback.answer()
        return

    await disable_reminder(callback, callback_data, user_service, habit_service)


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
        await callback.answer("Сначала отправь /start.", show_alert=True)
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

    text, reply_markup = build_habit_return_view(
        habit_card,
        callback_data.source,
        callback_data.return_to,
    )
    await callback.message.edit_text(text, reply_markup=reply_markup)
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
        await message.answer("Сначала отправь /start.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Пришли своё текущее местное время или нажми «Отмена».")
        return

    state_data = await state.get_data()
    habit_id = state_data.get("habit_id")
    source = state_data.get("source")
    return_to = state_data.get("return_to")
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")

    if (
        not isinstance(habit_id, int)
        or not isinstance(source, str)
        or not isinstance(return_to, str)
        or not isinstance(prompt_chat_id, int)
        or not isinstance(prompt_message_id, int)
    ):
        await state.clear()
        await message.answer("Не получилось продолжить настройку. Открой привычку ещё раз.")
        return

    try:
        await user_service.set_utc_offset_from_local_time(user.id, message.text or "")
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
        text=_build_reminder_time_prompt_text(habit_card.title, reminder_state),
        reply_markup=get_habit_reminder_input_keyboard(
            habit_card.id,
            source,
            return_to,
        ),
    )
    await state.update_data(
        prompt_chat_id=new_prompt_chat_id,
        prompt_message_id=new_prompt_message_id,
    )

    await message.answer("Запомнил твоё местное время. Теперь укажи время напоминания.")


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
        await message.answer("Сначала отправь /start.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Пришли время напоминания или нажми «Отмена».")
        return

    state_data = await state.get_data()
    habit_id = state_data.get("habit_id")
    source = state_data.get("source")
    return_to = state_data.get("return_to")
    mode = state_data.get("mode")
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")

    if (
        not isinstance(habit_id, int)
        or not isinstance(source, str)
        or not isinstance(return_to, str)
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
    text, reply_markup = build_habit_return_view(habit_card, source, return_to)
    await _render_message(
        bot=message.bot,
        chat_id=prompt_chat_id,
        message_id=prompt_message_id,
        text=text,
        reply_markup=reply_markup,
    )
    await message.answer(success_text)


def _build_reminder_menu_text(
    title: str,
    frequency_text: str,
    reminder_state: HabitReminderState,
    local_time_status: str | None,
    is_active: bool,
) -> str:
    reminder_time = (
        reminder_state.reminder_time.strftime("%H:%M")
        if reminder_state.enabled and reminder_state.reminder_time is not None
        else "не настроено"
    )

    lines = [
        f"⏰ Напоминание для «{html.quote(title)}»",
        "",
        f"Частота: {frequency_text}",
        f"Сейчас: {'включено' if reminder_state.enabled else 'выключено'}",
        f"Время: {reminder_time}",
        (
            f"Твоё местное время: {local_time_status}"
            if local_time_status is not None
            else "Твоё местное время пока не настроено."
        ),
    ]

    if not is_active:
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


def _build_current_local_time_prompt_text(title: str) -> str:
    return "\n".join(
        [
            f"⏰ Напоминание для «{html.quote(title)}»",
            "",
            "Сначала напиши, сколько у тебя сейчас времени.",
            "Формат: ЧЧ:ММ",
            "Например: 21:35",
        ]
    )


def _build_reminder_time_prompt_text(
    title: str,
    reminder_state: HabitReminderState,
) -> str:
    lines = [
        f"⏰ Напоминание для «{html.quote(title)}»",
        "",
        "Теперь напиши время напоминания.",
        "Формат: ЧЧ:ММ",
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


def _parse_legacy_reminder_menu_callback(data: str | None) -> HabitReminderMenuCallback | None:
    parsed = _parse_legacy_habit_callback(data, prefix="habit_reminder_menu")
    if parsed is None:
        return None

    habit_id, source = parsed
    return HabitReminderMenuCallback(
        habit_id=habit_id,
        source=source,
        return_to=HabitReturnTarget.CARD.value,
    )


def _parse_legacy_reminder_action_callback(
    data: str | None,
    *,
    prefix: str,
    callback_factory,
):
    parsed = _parse_legacy_habit_callback(data, prefix=prefix)
    if parsed is None:
        return None

    habit_id, source = parsed
    return callback_factory(
        habit_id=habit_id,
        source=source,
        return_to=HabitReturnTarget.CARD.value,
    )


def _parse_legacy_habit_callback(
    data: str | None,
    *,
    prefix: str,
) -> tuple[int, str] | None:
    if data is None:
        return None

    parts = data.split(":", maxsplit=2)
    if len(parts) != 3 or parts[0] != prefix:
        return None

    try:
        habit_id = int(parts[1])
    except ValueError:
        return None

    return habit_id, parts[2]
