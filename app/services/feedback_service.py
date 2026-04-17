"""Приём обратной связи, админский просмотр и хелперы для ответов."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from aiogram import html
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.repositories.feedback_repository import FeedbackRepository
from app.repositories.user_repository import UserRepository

if TYPE_CHECKING:
    from app.services.admin_action_log_service import AdminActionLogService


FEEDBACK_PREVIEW_LENGTH = 32
FEEDBACK_PAGE_SIZE = 6


class FeedbackServiceError(Exception):
    pass


class FeedbackAccessDeniedError(FeedbackServiceError):
    pass


class FeedbackNotFoundError(FeedbackServiceError):
    pass


class FeedbackValidationError(FeedbackServiceError):
    pass


@dataclass(slots=True)
class FeedbackDestination:
    admin_telegram_ids: list[int]
    support_contact_username: str | None

    @property
    def has_admin_recipients(self) -> bool:
        return bool(self.admin_telegram_ids)

    @property
    def has_contact(self) -> bool:
        return self.support_contact_username is not None


@dataclass(slots=True)
class FeedbackListItem:
    id: int
    user_id: int
    telegram_id: int
    username: str | None
    full_name: str | None
    created_at: datetime
    preview_text: str
    is_read: bool
    has_reply: bool


@dataclass(slots=True)
class FeedbackListPage:
    items: list[FeedbackListItem]
    page: int
    total_items: int
    total_pages: int
    has_prev: bool
    has_next: bool


@dataclass(slots=True)
class FeedbackCard:
    id: int
    user_id: int
    telegram_id: int
    username: str | None
    full_name: str | None
    created_at: datetime
    message_text: str
    is_read: bool
    admin_reply_text: str | None
    admin_replied_at: datetime | None


@dataclass(slots=True)
class PreparedFeedbackReply:
    feedback_id: int
    recipient_telegram_id: int
    recipient_display_name: str
    reply_text: str


class FeedbackService:
    def __init__(
        self,
        session: AsyncSession,
        user_repository: UserRepository,
        feedback_repository: FeedbackRepository,
        admin_action_log_service: "AdminActionLogService",
    ) -> None:
        self._session = session
        self._user_repository = user_repository
        self._feedback_repository = feedback_repository
        self._admin_action_log_service = admin_action_log_service

    async def get_feedback_destination(self) -> FeedbackDestination:
        admin_users = await self._user_repository.get_admin_users()
        return FeedbackDestination(
            admin_telegram_ids=[user.telegram_id for user in admin_users],
            support_contact_username=self.normalize_contact_username(
                settings.feedback_contact_username
            ),
        )

    async def create_feedback(self, author_user_id: int, message_text: str) -> FeedbackCard:
        author = await self._user_repository.get_by_id(author_user_id)
        if author is None:
            raise FeedbackValidationError("Пользователь не найден.")

        normalized_text = self._normalize_feedback_text(message_text)
        feedback = await self._feedback_repository.create_feedback(
            user_id=author.id,
            message_text=normalized_text,
        )
        await self._session.commit()
        await self._session.refresh(feedback)
        return FeedbackCard(
            id=feedback.id,
            user_id=author.id,
            telegram_id=author.telegram_id,
            username=author.username,
            full_name=self._build_full_name(author),
            created_at=feedback.created_at,
            message_text=feedback.message_text,
            is_read=feedback.is_read,
            admin_reply_text=feedback.admin_reply_text,
            admin_replied_at=feedback.admin_replied_at,
        )

    async def get_feedback_page_for_admin(
        self,
        actor_telegram_id: int,
        *,
        page: int = 1,
        page_size: int = FEEDBACK_PAGE_SIZE,
    ) -> FeedbackListPage:
        await self._ensure_admin(actor_telegram_id)
        total_items = await self._feedback_repository.count_feedback()
        resolved_page, total_pages, offset = self._resolve_page(
            requested_page=page,
            total_items=total_items,
            page_size=page_size,
        )
        feedback_messages = await self._feedback_repository.list_feedback(
            limit=page_size,
            offset=offset,
        )
        return FeedbackListPage(
            items=[self._build_feedback_list_item(item) for item in feedback_messages],
            page=resolved_page,
            total_items=total_items,
            total_pages=total_pages,
            has_prev=resolved_page > 1,
            has_next=resolved_page < total_pages,
        )

    async def get_feedback_list_for_admin(
        self,
        actor_telegram_id: int,
        *,
        limit: int = 20,
    ) -> list[FeedbackListItem]:
        page = await self.get_feedback_page_for_admin(
            actor_telegram_id,
            page=1,
            page_size=limit,
        )
        return page.items

    async def get_feedback_card_for_admin(
        self,
        actor_telegram_id: int,
        feedback_id: int,
        *,
        mark_as_read: bool = True,
    ) -> FeedbackCard:
        await self._ensure_admin(actor_telegram_id)
        feedback = await self._feedback_repository.get_feedback_by_id(feedback_id)
        if feedback is None or feedback.user is None:
            raise FeedbackNotFoundError("Сообщение обратной связи не найдено.")

        if mark_as_read and not feedback.is_read:
            await self._feedback_repository.mark_as_read(feedback)
            await self._session.commit()

        return self._build_feedback_card(feedback)

    async def prepare_feedback_reply(
        self,
        actor_telegram_id: int,
        feedback_id: int,
        reply_text: str,
    ) -> PreparedFeedbackReply:
        await self._ensure_admin(actor_telegram_id)
        feedback = await self._feedback_repository.get_feedback_by_id(feedback_id)
        if feedback is None or feedback.user is None:
            raise FeedbackNotFoundError("Сообщение не найдено.")

        normalized_reply_text = self._normalize_message_text(
            reply_text,
            empty_message="Напиши текст ответа.",
        )
        return PreparedFeedbackReply(
            feedback_id=feedback.id,
            recipient_telegram_id=feedback.user.telegram_id,
            recipient_display_name=self._build_person_label(feedback.user),
            reply_text=normalized_reply_text,
        )

    async def save_admin_reply(
        self,
        actor_telegram_id: int,
        feedback_id: int,
        reply_text: str,
    ) -> FeedbackCard:
        actor = await self._ensure_admin(actor_telegram_id)
        feedback = await self._feedback_repository.get_feedback_by_id(feedback_id)
        if feedback is None or feedback.user is None:
            raise FeedbackNotFoundError("Сообщение не найдено.")

        normalized_reply_text = self._normalize_message_text(
            reply_text,
            empty_message="Напиши текст ответа.",
        )
        await self._feedback_repository.save_admin_reply(
            feedback,
            normalized_reply_text,
            datetime.now(timezone.utc),
        )
        await self._admin_action_log_service.log_feedback_reply(
            actor_user_id=actor.id,
            target_user_id=feedback.user.id,
            feedback_id=feedback.id,
            reply_text=normalized_reply_text,
            feedback_preview=self._build_preview_text(feedback.message_text),
        )
        await self._session.commit()
        return self._build_feedback_card(feedback)

    async def count_unread_feedback_for_admin(self, actor_telegram_id: int) -> int:
        await self._ensure_admin(actor_telegram_id)
        return await self._feedback_repository.count_unread_feedback()

    async def count_feedback_for_admin(self, actor_telegram_id: int) -> int:
        await self._ensure_admin(actor_telegram_id)
        return await self._feedback_repository.count_feedback()

    @staticmethod
    def build_feedback_message(author: User, text: str, feedback_id: int) -> str:
        username = f"@{author.username}" if author.username else "не указан"
        full_name = FeedbackService._build_full_name(author) or "не указано"
        return "\n".join(
            [
                "💬 Новая обратная связь",
                "",
                f"Номер сообщения: {feedback_id}",
                f"Пользователь: {html.quote(full_name)}",
                f"Идентификатор Telegram: {author.telegram_id}",
                f"Имя пользователя: {html.quote(username)}",
                "",
                "Текст:",
                html.quote(text),
                "",
                "Открыть можно в разделе «Обратная связь» в /admin.",
            ]
        )

    @staticmethod
    def build_admin_reply_message(reply_text: str) -> str:
        return "\n".join(
            [
                "💬 Ответ от команды",
                "",
                html.quote(reply_text),
            ]
        )

    @staticmethod
    def normalize_contact_username(username: str | None) -> str | None:
        if username is None:
            return None

        normalized_username = username.strip()
        if not normalized_username:
            return None

        if normalized_username.startswith("@"):
            return normalized_username
        return f"@{normalized_username}"

    async def _ensure_admin(self, actor_telegram_id: int) -> User:
        actor = await self._user_repository.get_by_telegram_id(actor_telegram_id)
        if actor is None or not actor.is_admin or actor.is_blocked:
            raise FeedbackAccessDeniedError("Этот раздел доступен только администратору.")
        return actor

    @staticmethod
    def _build_feedback_list_item(feedback) -> FeedbackListItem:
        user = feedback.user
        return FeedbackListItem(
            id=feedback.id,
            user_id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            full_name=FeedbackService._build_full_name(user),
            created_at=feedback.created_at,
            preview_text=FeedbackService._build_preview_text(feedback.message_text),
            is_read=feedback.is_read,
            has_reply=feedback.admin_reply_text is not None,
        )

    @staticmethod
    def _build_feedback_card(feedback) -> FeedbackCard:
        user = feedback.user
        return FeedbackCard(
            id=feedback.id,
            user_id=user.id,
            telegram_id=user.telegram_id,
            username=user.username,
            full_name=FeedbackService._build_full_name(user),
            created_at=feedback.created_at,
            message_text=feedback.message_text,
            is_read=feedback.is_read,
            admin_reply_text=feedback.admin_reply_text,
            admin_replied_at=feedback.admin_replied_at,
        )

    @staticmethod
    def _normalize_feedback_text(message_text: str) -> str:
        return FeedbackService._normalize_message_text(
            message_text,
            empty_message="Нужен текст сообщения.",
        )

    @staticmethod
    def _normalize_message_text(message_text: str, *, empty_message: str) -> str:
        normalized_text = message_text.strip()
        if not normalized_text:
            raise FeedbackValidationError(empty_message)
        return normalized_text

    @staticmethod
    def _build_full_name(user: User) -> str | None:
        full_name = " ".join(part for part in [user.first_name, user.last_name] if part)
        return full_name or None

    @staticmethod
    def _build_person_label(user: User) -> str:
        if user.username:
            return f"@{user.username}"
        full_name = FeedbackService._build_full_name(user)
        if full_name is not None:
            return full_name
        return str(user.telegram_id)

    @staticmethod
    def _build_preview_text(message_text: str) -> str:
        normalized_text = " ".join(message_text.split())
        if len(normalized_text) <= FEEDBACK_PREVIEW_LENGTH:
            return normalized_text
        return f"{normalized_text[:FEEDBACK_PREVIEW_LENGTH - 1]}…"

    @staticmethod
    def _resolve_page(
        *,
        requested_page: int,
        total_items: int,
        page_size: int,
    ) -> tuple[int, int, int]:
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        page = min(max(requested_page, 1), total_pages)
        offset = (page - 1) * page_size
        return page, total_pages, offset
