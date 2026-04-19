"""Общие тестовые заглушки и фабрики объектов."""

from datetime import date, datetime, timezone
from types import SimpleNamespace


class DummySession:
    def __init__(self) -> None:
        self.commit_calls = 0
        self.refresh_calls: list[object] = []
        self.rollback_calls = 0

    async def commit(self) -> None:
        self.commit_calls += 1

    async def refresh(self, obj: object) -> None:
        self.refresh_calls.append(obj)

    async def rollback(self) -> None:
        self.rollback_calls += 1


def make_habit(**overrides: object) -> SimpleNamespace:
    created_at = datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc)
    # Значения по умолчанию делают тесты компактнее, но при этом создают
    # объект, у которого есть все атрибуты, нужные сервисам.
    defaults = {
        "id": 1,
        "user_id": 1,
        "title": "Read 20 pages",
        "frequency_type": "daily",
        "frequency_interval": None,
        "week_days_mask": None,
        "start_date": date(2026, 4, 4),
        "is_active": True,
        "is_paused": False,
        "paused_at": None,
        "is_deleted": False,
        "reminder_enabled": False,
        "reminder_time": None,
        "goal_type": None,
        "goal_target_value": None,
        "goal_achieved_at": None,
        "created_at": created_at,
        "last_completed_at": None,
        "user": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def make_user(**overrides: object) -> SimpleNamespace:
    # Тестовые пользователи повторяют форму объектов, которую ждут сервисы
    # и промежуточные слои, но не требуют настоящих ORM-экземпляров.
    defaults = {
        "id": 1,
        "telegram_id": 123456,
        "username": "stonebridgeway",
        "first_name": "Sasha",
        "last_name": None,
        "is_admin": False,
        "is_blocked": False,
        "utc_offset_minutes": 180,
        "last_daily_summary_sent_for_date": None,
        "last_weekly_summary_sent_for_week_start": None,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)
