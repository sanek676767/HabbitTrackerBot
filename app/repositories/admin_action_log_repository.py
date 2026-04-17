"""Хелперы доступа к данным записей журнала действий администратора."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin_action_log import AdminActionLog


class AdminActionLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_log(
        self,
        *,
        actor_user_id: int,
        action_type: str,
        entity_type: str,
        target_user_id: int | None = None,
        entity_id: int | None = None,
        details_json: dict[str, Any] | None = None,
    ) -> AdminActionLog:
        log = AdminActionLog(
            actor_user_id=actor_user_id,
            target_user_id=target_user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details_json=details_json,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def list_logs(
        self,
        *,
        limit: int,
        offset: int,
    ) -> list[AdminActionLog]:
        statement = (
            select(AdminActionLog)
            .options(
                selectinload(AdminActionLog.actor_user),
                selectinload(AdminActionLog.target_user),
            )
            .order_by(AdminActionLog.created_at.desc(), AdminActionLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def list_logs_by_actor(
        self,
        actor_user_id: int,
        *,
        limit: int,
        offset: int,
    ) -> list[AdminActionLog]:
        statement = (
            select(AdminActionLog)
            .options(
                selectinload(AdminActionLog.actor_user),
                selectinload(AdminActionLog.target_user),
            )
            .where(AdminActionLog.actor_user_id == actor_user_id)
            .order_by(AdminActionLog.created_at.desc(), AdminActionLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def list_logs_by_target(
        self,
        target_user_id: int,
        *,
        limit: int,
        offset: int,
    ) -> list[AdminActionLog]:
        statement = (
            select(AdminActionLog)
            .options(
                selectinload(AdminActionLog.actor_user),
                selectinload(AdminActionLog.target_user),
            )
            .where(AdminActionLog.target_user_id == target_user_id)
            .order_by(AdminActionLog.created_at.desc(), AdminActionLog.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.scalars(statement)
        return list(result)

    async def get_log_by_id(self, log_id: int) -> AdminActionLog | None:
        statement = (
            select(AdminActionLog)
            .options(
                selectinload(AdminActionLog.actor_user),
                selectinload(AdminActionLog.target_user),
            )
            .where(AdminActionLog.id == log_id)
        )
        return await self._session.scalar(statement)

    async def count_logs(self) -> int:
        statement = select(func.count(AdminActionLog.id))
        result = await self._session.scalar(statement)
        return int(result or 0)
