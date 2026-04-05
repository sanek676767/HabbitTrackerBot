"""Add habit schedule fields

Revision ID: 0009_add_habit_schedules
Revises: 0008_add_feedback_reply_fields
Create Date: 2026-04-05 20:10:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0009_add_habit_schedules"
down_revision: Union[str, None] = "0008_add_feedback_reply_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "habits",
        sa.Column("frequency_interval", sa.Integer(), nullable=True),
    )
    op.add_column(
        "habits",
        sa.Column("week_days_mask", sa.Integer(), nullable=True),
    )
    op.add_column(
        "habits",
        sa.Column("start_date", sa.Date(), nullable=True),
    )

    op.execute(sa.text("UPDATE habits SET start_date = DATE(created_at) WHERE start_date IS NULL"))

    op.alter_column(
        "habits",
        "start_date",
        existing_type=sa.Date(),
        nullable=False,
        server_default=sa.text("CURRENT_DATE"),
    )


def downgrade() -> None:
    op.drop_column("habits", "start_date")
    op.drop_column("habits", "week_days_mask")
    op.drop_column("habits", "frequency_interval")
