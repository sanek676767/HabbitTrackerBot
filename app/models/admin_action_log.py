"""Модель ORM для журнала действий администратора."""

from typing import Any

from sqlalchemy import BigInteger, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin


class AdminActionLog(IdMixin, CreatedAtMixin, Base):
    __tablename__ = "admin_action_logs"
    __table_args__ = (
        Index("ix_admin_action_logs_created_at", "created_at"),
        Index(
            "ix_admin_action_logs_actor_user_id_created_at",
            "actor_user_id",
            "created_at",
        ),
        Index(
            "ix_admin_action_logs_target_user_id_created_at",
            "target_user_id",
            "created_at",
        ),
    )

    actor_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )
    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    details_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    actor_user = relationship("User", foreign_keys=[actor_user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])
