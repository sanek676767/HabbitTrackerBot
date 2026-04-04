from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, text
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

    user = relationship("User", back_populates="habits")
    logs = relationship(
        "HabitLog",
        back_populates="habit",
        cascade="all, delete-orphan",
    )
