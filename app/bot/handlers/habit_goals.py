from aiogram import F, Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import HabitGoalActionCallback, HabitGoalMenuCallback, HabitReturnTarget
from app.bot.habit_text import build_habit_card_text, build_habit_edit_menu_text
from app.bot.keyboards import (
    ALL_MAIN_MENU_BUTTONS,
    get_habit_card_keyboard,
    get_habit_edit_keyboard,
    get_habit_goal_input_keyboard,
    get_habit_goal_menu_keyboard,
)
from app.services.habit_goal_service import HabitGoalService
from app.services.habit_service import (
    HabitDeletedError,
    HabitNotFoundError,
    HabitService,
    HabitValidationError,
)
from app.services.user_service import UserService


router = Router(name="habit_goals")


class HabitGoalStates(StatesGroup):
    waiting_for_target_value = State()


@router.callback_query(F.data.regexp(r"^habit_goal_menu:\d+:[^:]+$"))
async def open_goal_menu_legacy(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    callback_data = _parse_legacy_goal_menu_callback(callback.data)
    if callback_data is None:
        await callback.answer()
        return

    await open_goal_menu(callback, callback_data, state, user_service, habit_service)


@router.callback_query(HabitGoalMenuCallback.filter())
async def open_goal_menu(
    callback: CallbackQuery,
    callback_data: HabitGoalMenuCallback,
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
    await callback.message.edit_text(
        _build_goal_menu_text(habit_card.title, habit_card.goal),
        reply_markup=get_habit_goal_menu_keyboard(
            habit_card.id,
            callback_data.source,
            has_goal=habit_card.goal is not None,
            return_to=callback_data.return_to,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.regexp(r"^habit_goal_action:[^:]+:\d+:[^:]+$"))
async def handle_goal_action_legacy(
    callback: CallbackQuery,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    callback_data = _parse_legacy_goal_action_callback(callback.data)
    if callback_data is None:
        await callback.answer()
        return

    if callback_data.action == "back":
        await close_goal_menu(callback, callback_data, state, user_service, habit_service)
        return

    if callback_data.action == "clear":
        await clear_goal(callback, callback_data, state, user_service, habit_service)
        return

    await start_goal_setup(callback, callback_data, state, user_service, habit_service)


@router.callback_query(HabitGoalActionCallback.filter(F.action == "back"))
async def close_goal_menu(
    callback: CallbackQuery,
    callback_data: HabitGoalActionCallback,
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
    if callback_data.return_to == HabitReturnTarget.EDIT.value:
        await callback.message.edit_text(
            build_habit_edit_menu_text(habit_card),
            reply_markup=get_habit_edit_keyboard(habit_card.id, callback_data.source),
        )
    else:
        await callback.message.edit_text(
            build_habit_card_text(habit_card),
            reply_markup=get_habit_card_keyboard(
                habit_card.id,
                callback_data.source,
                is_completed_today=habit_card.is_completed_today,
                is_active=habit_card.is_active,
                is_due_today=habit_card.is_due_today,
            ),
        )
    await callback.answer()


@router.callback_query(HabitGoalActionCallback.filter(F.action == "clear"))
async def clear_goal(
    callback: CallbackQuery,
    callback_data: HabitGoalActionCallback,
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
        habit_card = await habit_service.clear_habit_goal(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        build_habit_card_text(habit_card),
        reply_markup=get_habit_card_keyboard(
            habit_card.id,
            callback_data.source,
            is_completed_today=habit_card.is_completed_today,
            is_active=habit_card.is_active,
            is_due_today=habit_card.is_due_today,
        ),
    )
    await callback.answer("Цель убрал.")


@router.callback_query(HabitGoalActionCallback.filter())
async def start_goal_setup(
    callback: CallbackQuery,
    callback_data: HabitGoalActionCallback,
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

    if callback_data.action == "back_to_menu":
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
            _build_goal_menu_text(habit_card.title, habit_card.goal),
            reply_markup=get_habit_goal_menu_keyboard(
                habit_card.id,
                callback_data.source,
                has_goal=habit_card.goal is not None,
                return_to=callback_data.return_to,
            ),
        )
        await callback.answer()
        return

    if callback_data.action not in {"completions", "streak"}:
        await callback.answer()
        return

    try:
        habit_card = await habit_service.get_habit_card(user.id, callback_data.habit_id)
    except HabitNotFoundError:
        await callback.answer("Привычка не найдена.", show_alert=True)
        return
    except HabitDeletedError as error:
        await callback.answer(str(error), show_alert=True)
        return

    goal_type = (
        HabitGoalService.COMPLETIONS
        if callback_data.action == "completions"
        else HabitGoalService.STREAK
    )
    await state.set_state(HabitGoalStates.waiting_for_target_value)
    await state.update_data(
        habit_id=habit_card.id,
        source=callback_data.source,
        return_to=callback_data.return_to,
        goal_type=goal_type,
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
    )
    await callback.message.edit_text(
        _build_goal_value_prompt_text(goal_type, habit_card.title),
        reply_markup=get_habit_goal_input_keyboard(
            habit_card.id,
            callback_data.source,
            callback_data.return_to,
        ),
    )
    await callback.answer()


@router.message(HabitGoalStates.waiting_for_target_value)
async def save_goal(
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
        await message.answer("Пришли число цели или вернись назад кнопкой под сообщением.")
        return

    state_data = await state.get_data()
    habit_id = state_data.get("habit_id")
    source = state_data.get("source")
    goal_type = state_data.get("goal_type")
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")

    if (
        not isinstance(habit_id, int)
        or not isinstance(source, str)
        or not isinstance(goal_type, str)
        or not isinstance(prompt_chat_id, int)
        or not isinstance(prompt_message_id, int)
    ):
        await state.clear()
        await message.answer("Не получилось продолжить настройку цели. Открой привычку ещё раз.")
        return

    try:
        target_value = int((message.text or "").strip())
    except ValueError:
        await message.answer("Напиши цель числом.")
        return

    try:
        habit_card = await habit_service.update_habit_goal(
            user.id,
            habit_id,
            goal_type=goal_type,
            goal_target_value=target_value,
        )
    except HabitValidationError as error:
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
    await _render_card_message(
        bot=message.bot,
        chat_id=prompt_chat_id,
        message_id=prompt_message_id,
        habit_card=habit_card,
        source=source,
    )
    await message.answer("Цель обновил.")


def _build_goal_menu_text(title: str, goal) -> str:
    lines = [
        f"🎯 Цель для «{html.quote(title)}»",
        "",
    ]

    if goal is None:
        lines.extend(
            [
                "Цель пока не задана.",
                "",
                "Выбери тип цели ниже.",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            f"Текущая цель: {goal.goal_text}",
            f"Прогресс: {goal.progress_text}",
            (
                "Результат: цель достигнута"
                if goal.is_achieved
                else "Результат: цель ещё в работе"
            ),
            "",
            "Можно изменить цель или убрать её.",
        ]
    )
    return "\n".join(lines)


def _build_goal_value_prompt_text(goal_type: str, title: str) -> str:
    if goal_type == HabitGoalService.COMPLETIONS:
        return "\n".join(
            [
                f"🎯 Цель для «{html.quote(title)}»",
                "",
                "Напиши, сколько выполнений хочешь набрать.",
                "Например: 20",
            ]
        )

    return "\n".join(
        [
            f"🎯 Цель для «{html.quote(title)}»",
            "",
            "Напиши, до какой серии хочешь дойти.",
            "Например: 14",
        ]
    )


async def _render_card_message(
    *,
    bot,
    chat_id: int,
    message_id: int,
    habit_card,
    source: str,
) -> tuple[int, int]:
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=build_habit_card_text(habit_card),
            reply_markup=get_habit_card_keyboard(
                habit_card.id,
                source,
                is_completed_today=habit_card.is_completed_today,
                is_active=habit_card.is_active,
                is_due_today=habit_card.is_due_today,
            ),
        )
        return chat_id, message_id
    except TelegramBadRequest:
        sent_message = await bot.send_message(
            chat_id=chat_id,
            text=build_habit_card_text(habit_card),
            reply_markup=get_habit_card_keyboard(
                habit_card.id,
                source,
                is_completed_today=habit_card.is_completed_today,
                is_active=habit_card.is_active,
                is_due_today=habit_card.is_due_today,
            ),
        )
        return sent_message.chat.id, sent_message.message_id


def _parse_legacy_goal_menu_callback(data: str | None) -> HabitGoalMenuCallback | None:
    parsed = _parse_legacy_habit_callback(data, prefix="habit_goal_menu")
    if parsed is None:
        return None

    habit_id, source = parsed
    return HabitGoalMenuCallback(
        habit_id=habit_id,
        source=source,
        return_to=HabitReturnTarget.CARD.value,
    )


def _parse_legacy_goal_action_callback(data: str | None) -> HabitGoalActionCallback | None:
    if data is None:
        return None

    parts = data.split(":", maxsplit=3)
    if len(parts) != 4 or parts[0] != "habit_goal_action":
        return None

    try:
        habit_id = int(parts[2])
    except ValueError:
        return None

    return HabitGoalActionCallback(
        action=parts[1],
        habit_id=habit_id,
        source=parts[3],
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
