from datetime import datetime, time
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Time, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin, UpdatedAtMixin


class HabitFrequencyType(str, Enum):
    DAILY = "daily"


class Habit(IdMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "habits"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=HabitFrequencyType.DAILY.value,
        server_default=text("'daily'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    reminder_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    reminder_time: Mapped[time | None] = mapped_column(
        Time(),
        nullable=True,
    )

    user = relationship("User", back_populates="habits")
    logs = relationship(
        "HabitLog",
        back_populates="habit",
        cascade="all, delete-orphan",
    )
