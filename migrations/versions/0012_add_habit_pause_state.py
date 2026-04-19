"""Add habit pause state

Revision ID: 0012_add_habit_pause_state
Revises: 0011_add_habit_goals
Create Date: 2026-04-19 19:20:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0012_add_habit_pause_state"
down_revision: Union[str, None] = "0011_add_habit_goals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "habits",
        sa.Column(
            "is_paused",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "habits",
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(sa.text("UPDATE habits SET is_paused = false WHERE is_paused IS NULL"))

    op.alter_column(
        "habits",
        "is_paused",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("false"),
    )


def downgrade() -> None:
    op.drop_column("habits", "paused_at")
    op.drop_column("habits", "is_paused")
