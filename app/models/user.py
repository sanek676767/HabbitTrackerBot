from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, IdMixin, UpdatedAtMixin


class User(IdMixin, CreatedAtMixin, UpdatedAtMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
    )
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    is_blocked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0"),
    )
    current_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("plans.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    plan_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    current_plan = relationship(
        "Plan",
        back_populates="users_on_plan",
        foreign_keys=[current_plan_id],
    )
    subscriptions = relationship(
        "Subscription",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    payments = relationship(
        "Payment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    tasks = relationship(
        "Task",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    habits = relationship(
        "Habit",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    usage_logs = relationship(
        "UsageLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )
