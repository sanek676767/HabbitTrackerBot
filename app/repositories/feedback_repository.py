from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.feedback_message import FeedbackMessage


class FeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_feedback(self, user_id: int, message_text: str) -> FeedbackMessage:
        feedback = FeedbackMessage(
            user_id=user_id,
            message_text=message_text,
        )
        self._session.add(feedback)
        await self._session.flush()
        return feedback

    async def list_feedback(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[FeedbackMessage]:
        statement = (
            select(FeedbackMessage)
            .options(selectinload(FeedbackMessage.user))
            .order_by(FeedbackMessage.created_at.desc(), FeedbackMessage.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def list_unread_feedback(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[FeedbackMessage]:
        statement = (
            select(FeedbackMessage)
            .options(selectinload(FeedbackMessage.user))
            .where(FeedbackMessage.is_read.is_(False))
            .order_by(FeedbackMessage.created_at.desc(), FeedbackMessage.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def get_feedback_by_id(self, feedback_id: int) -> FeedbackMessage | None:
        statement = (
            select(FeedbackMessage)
            .options(selectinload(FeedbackMessage.user))
            .where(FeedbackMessage.id == feedback_id)
        )
        return await self._session.scalar(statement)

    async def mark_as_read(self, feedback: FeedbackMessage) -> FeedbackMessage:
        feedback.is_read = True
        await self._session.flush()
        return feedback

    async def save_admin_reply(
        self,
        feedback: FeedbackMessage,
        reply_text: str,
        replied_at: datetime,
    ) -> FeedbackMessage:
        feedback.admin_reply_text = reply_text
        feedback.admin_replied_at = replied_at
        feedback.is_read = True
        await self._session.flush()
        return feedback

    async def count_feedback(self) -> int:
        statement = select(func.count(FeedbackMessage.id))
        result = await self._session.scalar(statement)
        return int(result or 0)

    async def count_unread_feedback(self) -> int:
        statement = select(func.count(FeedbackMessage.id)).where(
            FeedbackMessage.is_read.is_(False)
        )
        result = await self._session.scalar(statement)
        return int(result or 0)
