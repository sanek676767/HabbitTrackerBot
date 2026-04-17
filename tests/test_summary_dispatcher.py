"""Тесты условий отправки сводок и защиты от дублей."""

from datetime import date, time

from app.bot.summary_dispatcher import (
    _should_send_daily_summary,
    _should_send_weekly_summary,
)


def test_daily_summary_duplicate_protection_blocks_same_date() -> None:
    result = _should_send_daily_summary(
        current_local_time=time(21, 0),
        current_local_date=date(2026, 4, 4),
        last_sent_for_date=date(2026, 4, 4),
    )

    assert result is False


def test_daily_summary_allows_first_send_for_day() -> None:
    result = _should_send_daily_summary(
        current_local_time=time(21, 0),
        current_local_date=date(2026, 4, 4),
        last_sent_for_date=date(2026, 4, 3),
    )

    assert result is True


def test_weekly_summary_duplicate_protection_blocks_same_week() -> None:
    result = _should_send_weekly_summary(
        current_local_time=time(20, 0),
        current_local_date=date(2026, 4, 5),
        last_sent_for_week_start=date(2026, 3, 30),
    )

    assert result is False


def test_weekly_summary_allows_first_send_for_week() -> None:
    result = _should_send_weekly_summary(
        current_local_time=time(20, 0),
        current_local_date=date(2026, 4, 5),
        last_sent_for_week_start=date(2026, 3, 23),
    )

    assert result is True
