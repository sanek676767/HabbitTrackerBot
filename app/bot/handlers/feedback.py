from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.callbacks import FeedbackCallback
from app.bot.keyboards import (
    ALL_MAIN_MENU_BUTTONS,
    FEEDBACK_BUTTON,
    get_feedback_keyboard,
    get_main_menu_keyboard,
)
from app.services.feedback_service import FeedbackService, FeedbackValidationError
from app.services.user_service import UserService


router = Router(name="feedback")


class FeedbackStates(StatesGroup):
    waiting_for_message = State()


@router.message(Command("feedback"))
@router.message(F.text == FEEDBACK_BUTTON)
async def start_feedback(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    feedback_service: FeedbackService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer("Сначала отправь /start.")
        return

    destination = await feedback_service.get_feedback_destination()
    if destination.has_admin_recipients:
        await state.set_state(FeedbackStates.waiting_for_message)
        await message.answer(
            "\n".join(
                [
                    "💬 Обратная связь",
                    "",
                    "Напиши одним сообщением, что хочется улучшить или что работает неудобно.",
                    "Я передам это команде.",
                ]
            ),
            reply_markup=get_feedback_keyboard(),
        )
        return

    contact_line = (
        f"Связаться можно здесь: {destination.support_contact_username}"
        if destination.has_contact
        else "Раздел обратной связи пока недоступен. Попробуй позже."
    )
    await message.answer(
        "\n".join(
            [
                "💬 Обратная связь",
                "",
                contact_line,
            ]
        ),
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(
    FeedbackStates.waiting_for_message,
    FeedbackCallback.filter(F.action == "cancel"),
)
async def cancel_feedback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()
    if callback.message is not None:
        await callback.message.edit_text("Сообщение не отправлено.")
        await callback.message.answer(
            "Если захочешь, можно вернуться к этому позже.",
            reply_markup=get_main_menu_keyboard(),
        )
    await callback.answer()


@router.message(FeedbackStates.waiting_for_message)
async def submit_feedback(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    feedback_service: FeedbackService,
) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    if (message.text or "") in ALL_MAIN_MENU_BUTTONS:
        await message.answer(
            "Сначала отправь сообщение или нажми «Отмена».",
            reply_markup=get_feedback_keyboard(),
        )
        return

    user = await user_service.get_by_telegram_id(message.from_user.id)
    if user is None:
        await state.clear()
        await message.answer("Сначала отправь /start.", reply_markup=get_main_menu_keyboard())
        return

    feedback_text = message.text or ""
    destination = await feedback_service.get_feedback_destination()
    if not destination.has_admin_recipients:
        await state.clear()
        contact_line = (
            f"Сейчас можно написать сюда: {destination.support_contact_username}"
            if destination.has_contact
            else "Раздел обратной связи пока недоступен."
        )
        await message.answer(
            "\n".join(
                [
                    "Сейчас не получилось передать сообщение.",
                    contact_line,
                ]
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    try:
        created_feedback = await feedback_service.create_feedback(user.id, feedback_text)
    except FeedbackValidationError as error:
        await message.answer(str(error), reply_markup=get_feedback_keyboard())
        return

    admin_message = feedback_service.build_feedback_message(
        user,
        created_feedback.message_text,
        created_feedback.id,
    )
    sent_count = 0
    for admin_telegram_id in destination.admin_telegram_ids:
        await message.bot.send_message(
            chat_id=admin_telegram_id,
            text=admin_message,
        )
        sent_count += 1

    await state.clear()
    confirmation_text = (
        "Спасибо. Сообщение передано."
        if sent_count
        else "Сообщение сохранено. Команда увидит его в разделе обратной связи."
    )
    await message.answer(
        confirmation_text,
        reply_markup=get_main_menu_keyboard(),
    )
