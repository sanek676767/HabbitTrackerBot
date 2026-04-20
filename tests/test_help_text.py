from app.bot.handlers.help import _build_help_text


def test_help_text_mentions_current_bot_features() -> None:
    text = _build_help_text()

    assert "HabbitTrackerBot помогает вести привычки" in text
    assert "«📋 Мои привычки»" in text
    assert "«📈 Прогресс»" in text
    assert "«👤 Профиль»" in text
    assert "выполнено" in text
    assert "пропущено" in text
    assert "не запланировано" in text
    assert "ждёт отметку" in text
    assert "«🗓 История»" in text
    assert "«💬 Обратная связь»" in text
