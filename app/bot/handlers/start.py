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
    text = (
        _build_onboarding_text(greeting_name)
        if is_created
        else _build_returning_user_text(greeting_name)
    )

    await message.answer(
        text,
        reply_markup=get_main_menu_keyboard(
            show_admin_button=UserService.should_show_admin_entry(user)
        ),
    )


def _build_onboarding_text(greeting_name: str) -> str:
    return "\n".join(
        [
            f"Привет, {greeting_name}!",
            "",
            "Это бот для привычек с понятным ритмом и без лишнего шума.",
            "",
            "Здесь можно:",
            "• добавлять привычки с удобным расписанием",
            "• отмечать то, что запланировано на сегодня",
            "• включать напоминания на удобное время",
            "• смотреть серии, прогресс и сводки",
            "",
            "С чего начать:",
            "1. Нажми «➕ Добавить привычку»",
            "2. Выбери частоту и, если нужно, включи напоминание",
            "3. Загляни в «🔥 Сегодня», чтобы отмечать выполнение",
            "",
            "Если захочешь быстро освоиться, открой «❓ Помощь».",
        ]
    )


def _build_returning_user_text(greeting_name: str) -> str:
    return "\n".join(
        [
            f"С возвращением, {greeting_name}.",
            "",
            "Главные разделы уже на месте:",
            "• «🔥 Сегодня» — что запланировано на сегодня",
            "• «📈 Прогресс» — как идёт общий ритм",
            "• «❓ Помощь» — коротко о том, как всё устроено",
        ]
    )
