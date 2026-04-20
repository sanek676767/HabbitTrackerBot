from pathlib import Path

from aiogram import Router, html
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile, Message

from app.bot.keyboards import get_main_menu_keyboard
from app.services.user_service import UserService


router = Router(name="start")
START_BANNER_PATH = Path(__file__).resolve().parents[1] / "assets" / "start_banner.png"


@router.message(CommandStart())
async def start_handler(message: Message, user_service: UserService) -> None:
    if message.from_user is None:
        await message.answer("Не удалось определить пользователя Telegram.")
        return

    user, _ = await user_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    greeting_name = html.quote(message.from_user.first_name or "друг")
    text = _build_start_text(greeting_name)

    reply_markup = get_main_menu_keyboard(
        show_admin_button=UserService.should_show_admin_entry(user)
    )
    if START_BANNER_PATH.exists():
        await message.answer_photo(
            photo=FSInputFile(START_BANNER_PATH),
            caption=text,
            reply_markup=reply_markup,
        )
        return

    await message.answer(text, reply_markup=reply_markup)


def _build_start_text(greeting_name: str) -> str:
    return "\n".join(
        [
            f"Привет, {greeting_name}!",
            "",
            "Это Telegram-бот для системной работы с привычками: от первого шага до устойчивого результата.",
            "",
            "Здесь ты можешь:",
            "• создавать привычки с разным расписанием — каждый день, через день или по выбранным дням недели",
            "• отмечать выполнение только в те дни, когда привычка действительно запланирована",
            "• включать напоминания на удобное время",
            "• ставить цели по количеству выполнений или по серии",
            "• отслеживать текущую и лучшую серию",
            "• смотреть историю привычки по дням",
            "• анализировать прогресс и статистику за разные периоды",
            "• ставить привычки на паузу, отправлять в архив и возвращать обратно",
            "• держать всё в одном понятном рабочем ритме",
            "",
            "С чего начать:",
            "1. Нажми «➕ Добавить привычку»",
            "2. Выбери название, расписание, напоминание и цель",
            "3. Открой «🔥 Сегодня», чтобы отмечать выполнение по плану",
            "4. Загляни в «📊 Прогресс» и историю, чтобы видеть динамику",
            "",
            "Если захочешь быстро разобраться во всех разделах, открой «❓ Помощь».",
        ]
    )
