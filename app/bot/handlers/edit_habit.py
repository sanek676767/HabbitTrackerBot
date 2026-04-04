from aiogram import Router, html
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import HabitEditCallback, HabitEditCancelCallback
from app.bot.keyboards import (
    ALL_MAIN_MENU_BUTTONS,
    get_habit_card_keyboard,
    get_habit_edit_keyboard,
)
from app.services.habit_service import (
    HabitCard,
    HabitDeletedError,
    HabitNotFoundError,
    HabitService,
    HabitValidationError,
)
from app.services.user_service import UserService


router = Router(name="edit_habit")


class EditHabitStates(StatesGroup):
    waiting_for_title = State()


@router.callback_query(HabitEditCallback.filter())
async def start_edit_habit(
    callback: CallbackQuery,
    callback_data: HabitEditCallback,
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

    await state.set_state(EditHabitStates.waiting_for_title)
    await state.update_data(
        habit_id=habit_card.id,
        source=callback_data.source,
        prompt_chat_id=callback.message.chat.id,
        prompt_message_id=callback.message.message_id,
    )
    await callback.message.edit_text(
        _build_edit_prompt_text(habit_card.title),
        reply_markup=get_habit_edit_keyboard(habit_card.id, callback_data.source),
    )
    await callback.answer()


@router.callback_query(
    EditHabitStates.waiting_for_title,
    HabitEditCancelCallback.filter(),
)
async def cancel_edit_habit(
    callback: CallbackQuery,
    callback_data: HabitEditCancelCallback,
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
    await callback.answer("Редактирование отменено.")


@router.message(EditHabitStates.waiting_for_title)
async def save_habit_title(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    habit_service: HabitService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await message.answer("Сначала отправьте /start.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer("Чтобы отменить редактирование, нажми «⬅️ Отмена» под сообщением.")
        return

    state_data = await state.get_data()
    habit_id = state_data.get("habit_id")
    source = state_data.get("source")
    prompt_chat_id = state_data.get("prompt_chat_id")
    prompt_message_id = state_data.get("prompt_message_id")

    if not isinstance(habit_id, int) or not isinstance(source, str):
        await state.clear()
        await message.answer("Сессия редактирования потеряна. Открой карточку привычки заново.")
        return

    try:
        habit_card = await habit_service.rename_habit(user.id, habit_id, message.text or "")
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
    if isinstance(prompt_chat_id, int) and isinstance(prompt_message_id, int):
        try:
            await message.bot.edit_message_text(
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
        except TelegramBadRequest:
            await message.answer(
                _build_habit_card_text(habit_card),
                reply_markup=get_habit_card_keyboard(
                    habit_card.id,
                    source,
                    is_completed_today=habit_card.is_completed_today,
                    is_active=habit_card.is_active,
                ),
            )

    await message.answer(f"Название привычки обновлено: «{html.quote(habit_card.title)}».")


def _build_edit_prompt_text(title: str) -> str:
    return "\n".join(
        [
            "✏️ Редактирование привычки",
            "",
            f"Текущее название: {html.quote(title)}",
            "Введите новое название:",
        ]
    )


def _build_habit_card_text(habit_card: HabitCard) -> str:
    today_status = "Выполнена" if habit_card.is_completed_today else "Не выполнена"
    active_status = "Активная" if habit_card.is_active else "В архиве"
    return "\n".join(
        [
            f"📌 {html.quote(habit_card.title)}",
            "",
            f"Сегодня: {today_status}",
            f"Всего выполнений: {habit_card.total_completions}",
            f"Текущая серия: {habit_card.current_streak}",
            f"Лучшая серия: {habit_card.best_streak}",
            f"Статус: {active_status}",
        ]
    )
