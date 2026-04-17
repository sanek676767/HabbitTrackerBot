"""Форматирование и проверка доступа для журнала админ-действий."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.admin_action_log_repository import AdminActionLogRepository
from app.repositories.user_repository import UserRepository


ADMIN_ACTION_LOG_PAGE_SIZE = 6
ACTION_TEXTS = {
    "block_user": "заблокировал пользователя",
    "unblock_user": "разблокировал пользователя",
    "grant_admin": "выдал права администратора",
    "revoke_admin": "снял права администратора",
    "restore_deleted_habit": "восстановил удалённую привычку",
    "reply_feedback": "ответил на обращение",
}
ENTITY_TEXTS = {
    "user": "пользователь",
    "habit": "привычка",
    "feedback": "обращение",
}
DETAIL_LABELS = {
    "habit_title": "Привычка",
    "feedback_reply_text": "Текст ответа",
    "feedback_preview": "Текст обращения",
}


class AdminActionLogServiceError(Exception):
    pass


class AdminActionLogAccessDeniedError(AdminActionLogServiceError):
    pass


class AdminActionLogNotFoundError(AdminActionLogServiceError):
    pass


@dataclass(slots=True)
class AdminActionLogPagination:
    page: int
    total_items: int
    total_pages: int
    has_prev: bool
    has_next: bool


@dataclass(slots=True)
class AdminActionLogDetailItem:
    label: str
    value: str


@dataclass(slots=True)
class AdminActionLogListItem:
    id: int
    summary_text: str
    actor_display_name: str
    action_text: str
    entity_text: str
    target_display_name: str | None
    created_at: datetime


@dataclass(slots=True)
class AdminActionLogPage:
    items: list[AdminActionLogListItem]
    pagination: AdminActionLogPagination


@dataclass(slots=True)
class AdminActionLogCard:
    id: int
    actor_display_name: str
    action_text: str
    entity_text: str
    target_display_name: str | None
    created_at: datetime
    details: list[AdminActionLogDetailItem]


class AdminActionLogService:
    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        admin_action_log_repository: AdminActionLogRepository,
    ) -> None:
        self._session = session
        self._user_repository = user_repository
        self._admin_action_log_repository = admin_action_log_repository

    async def create_log(
        self,
        *,
        actor_user_id: int,
        action_type: str,
        entity_type: str,
        target_user_id: int | None = None,
        entity_id: int | None = None,
        details_json: dict[str, Any] | None = None,
    ) -> None:
        await self._admin_action_log_repository.create_log(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details_json=details_json,
        )

    async def log_block_user(self, *, actor_user_id: int, target_user_id: int) -> None:
        await self.create_log(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type="block_user",
            entity_type="user",
            entity_id=target_user_id,
        )

    async def log_unblock_user(self, *, actor_user_id: int, target_user_id: int) -> None:
        await self.create_log(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type="unblock_user",
            entity_type="user",
            entity_id=target_user_id,
        )

    async def log_grant_admin(self, *, actor_user_id: int, target_user_id: int) -> None:
        await self.create_log(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type="grant_admin",
            entity_type="user",
            entity_id=target_user_id,
        )

    async def log_revoke_admin(self, *, actor_user_id: int, target_user_id: int) -> None:
        await self.create_log(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type="revoke_admin",
            entity_type="user",
            entity_id=target_user_id,
        )

    async def log_restore_deleted_habit(
        self,
        *,
        actor_user_id: int,
        target_user_id: int,
        habit_id: int,
        habit_title: str,
    ) -> None:
        await self.create_log(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type="restore_deleted_habit",
            entity_type="habit",
            entity_id=habit_id,
            details_json={"habit_title": habit_title},
        )

    async def log_feedback_reply(
        self,
        *,
        actor_user_id: int,
        target_user_id: int,
        feedback_id: int,
        reply_text: str,
        feedback_preview: str,
    ) -> None:
        await self.create_log(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type="reply_feedback",
            entity_type="feedback",
            entity_id=feedback_id,
            details_json={
                "feedback_reply_text": reply_text,
                "feedback_preview": feedback_preview,
            },
        )

    async def get_logs_page(
        self,
        actor_telegram_id: int,
        *,
        page: int,
        page_size: int = ADMIN_ACTION_LOG_PAGE_SIZE,
    ) -> AdminActionLogPage:
        await self._ensure_admin(actor_telegram_id)
        total_items = await self._admin_action_log_repository.count_logs()
        pagination = self._build_pagination(
            requested_page=page,
            total_items=total_items,
            page_size=page_size,
        )
        items = await self._admin_action_log_repository.list_logs(
            limit=page_size,
            offset=(pagination.page - 1) * page_size,
        )
        return AdminActionLogPage(
            items=[self._build_list_item(item) for item in items],
            pagination=pagination,
        )

    async def get_log_card(
        self,
        actor_telegram_id: int,
        log_id: int,
    ) -> AdminActionLogCard:
        await self._ensure_admin(actor_telegram_id)
        log = await self._admin_action_log_repository.get_log_by_id(log_id)
        if log is None:
            raise AdminActionLogNotFoundError("Запись в журнале не найдена.")
        return self._build_card(log)

    async def count_logs_for_admin(self, actor_telegram_id: int) -> int:
        await self._ensure_admin(actor_telegram_id)
        return await self._admin_action_log_repository.count_logs()

    async def _ensure_admin(self, actor_telegram_id: int) -> User:
        actor = await self._user_repository.get_by_telegram_id(actor_telegram_id)
        if actor is None or not actor.is_admin or actor.is_blocked:
            raise AdminActionLogAccessDeniedError(
                "Этот раздел доступен только администратору."
            )
        return actor

    @classmethod
    def _build_list_item(cls, log) -> AdminActionLogListItem:
        actor_display_name = cls._build_person_label(log.actor_user, fallback=str(log.actor_user_id))
        action_text = cls._get_action_text(log.action_type)
        entity_text = cls._build_entity_text(
            log.entity_type,
            log.entity_id,
            log.details_json,
        )
        target_display_name = cls._build_person_label(log.target_user) if log.target_user else None
        summary_text = cls._truncate_text(
            f"{actor_display_name} • {action_text} • {log.created_at.strftime('%d.%m %H:%M')}",
            64,
        )
        return AdminActionLogListItem(
            id=log.id,
            summary_text=summary_text,
            actor_display_name=actor_display_name,
            action_text=action_text,
            entity_text=entity_text,
            target_display_name=target_display_name,
            created_at=log.created_at,
        )

    @classmethod
    def _build_card(cls, log) -> AdminActionLogCard:
        actor_display_name = cls._build_person_label(log.actor_user, fallback=str(log.actor_user_id))
        target_display_name = cls._build_person_label(log.target_user) if log.target_user else None
        return AdminActionLogCard(
            id=log.id,
            actor_display_name=actor_display_name,
            action_text=cls._get_action_text(log.action_type),
            entity_text=cls._build_entity_text(
                log.entity_type,
                log.entity_id,
                log.details_json,
            ),
            target_display_name=target_display_name,
            created_at=log.created_at,
            details=cls._build_detail_items(log.details_json),
        )

    @staticmethod
    def _build_pagination(
        *,
        requested_page: int,
        total_items: int,
        page_size: int,
    ) -> AdminActionLogPagination:
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        page = min(max(requested_page, 1), total_pages)
        return AdminActionLogPagination(
            page=page,
            total_items=total_items,
            total_pages=total_pages,
            has_prev=page > 1,
            has_next=page < total_pages,
        )

    @staticmethod
    def _build_person_label(user: User | None, fallback: str | None = None) -> str:
        if user is None:
            return fallback or "неизвестный пользователь"
        if user.username:
            return f"@{user.username}"
        full_name = " ".join(part for part in [user.first_name, user.last_name] if part)
        if full_name:
            return full_name
        return str(user.telegram_id)

    @staticmethod
    def _get_action_text(action_type: str) -> str:
        return ACTION_TEXTS.get(action_type, action_type.replace("_", " "))

    @staticmethod
    def _build_entity_text(
        entity_type: str,
        entity_id: int | None,
        details_json: dict[str, Any] | None,
    ) -> str:
        if entity_type == "habit" and details_json is not None:
            habit_title = details_json.get("habit_title")
            if isinstance(habit_title, str) and habit_title:
                return f"привычка «{habit_title}»"

        base_text = ENTITY_TEXTS.get(entity_type, "сущность")
        if entity_id is None:
            return base_text
        return f"{base_text} #{entity_id}"

    @staticmethod
    def _build_detail_items(
        details_json: dict[str, Any] | None,
    ) -> list[AdminActionLogDetailItem]:
        if not details_json:
            return []

        items: list[AdminActionLogDetailItem] = []
        used_keys: set[str] = set()
        # Самые важные поля показываем первыми, чтобы карточка журнала
        # читалась естественно и без лишних прыжков по тексту.
        for key in ("habit_title", "feedback_preview", "feedback_reply_text"):
            value = details_json.get(key)
            if value is None:
                continue
            items.append(
                AdminActionLogDetailItem(
                    label=DETAIL_LABELS.get(key, key),
                    value=AdminActionLogService._stringify_detail_value(value),
                )
            )
            used_keys.add(key)

        for key, value in details_json.items():
            if key in used_keys or value is None:
                continue
            items.append(
                AdminActionLogDetailItem(
                    label=key.replace("_", " ").capitalize(),
                    value=AdminActionLogService._stringify_detail_value(value),
                )
            )

        return items

    @staticmethod
    def _stringify_detail_value(value: Any) -> str:
        if isinstance(value, list):
            return ", ".join(str(item) for item in value)
        if isinstance(value, dict):
            return ", ".join(f"{key}: {item}" for key, item in value.items())
        return str(value)

    @staticmethod
    def _truncate_text(value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value
        return f"{value[: max_length - 1]}…"
