from aiogram import Router, html
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards import get_main_menu_keyboard
from app.services.user_service import UserService


router = Router(name="start")


@router.message(CommandStart())
async def start_handler(message: Message, user_service: UserService) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user, is_created = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    greeting_name = html.quote(message.from_user.first_name or "друг")
    if is_created:
        text = _build_onboarding_text(greeting_name, user.id)
    else:
        text = _build_returning_user_text(greeting_name)

    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(),
    )


def _build_onboarding_text(greeting_name: str, user_id: int) -> str:
    return "\n".join(
        [
            f"Привет, {greeting_name}!",
            "",
            "Это бот для ежедневных привычек и спокойного ритма без лишнего шума.",
            f"Твой внутренний ID: {user_id}",
            "",
            "Что умеет бот:",
            "• создавать привычки и отмечать выполнение каждый день",
            "• напоминать в нужное время",
            "• считать streak, прогресс и weekly summary",
            "• хранить архив привычек, если ты хочешь убрать их из активных",
            "",
            "С чего начать:",
            "1. Нажми «➕ Добавить привычку»",
            "2. Открой «🔥 Сегодня», чтобы отмечать выполнение",
            "3. Загляни в «📈 Прогресс», чтобы увидеть общую картину",
            "",
            "Если захочешь быстро разобраться по функциям, открой «❓ Помощь».",
        ]
    )


def _build_returning_user_text(greeting_name: str) -> str:
    return "\n".join(
        [
            f"С возвращением, {greeting_name}.",
            "",
            "Главные кнопки уже на месте:",
            "• «🔥 Сегодня» — отметить привычки за день",
            "• «📈 Прогресс» — посмотреть общую картину",
            "• «❓ Помощь» — быстро вспомнить, как всё устроено",
        ]
    )
