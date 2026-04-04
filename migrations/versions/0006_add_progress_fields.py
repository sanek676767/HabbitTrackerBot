"""Add progress fields to habits and users

Revision ID: 0006_add_progress_fields
Revises: 0005_add_user_utc_offset
Create Date: 2026-04-04 18:55:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_add_progress_fields"
down_revision: Union[str, None] = "0005_add_user_utc_offset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "habits",
        sa.Column(
            "last_completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.execute(
        """
        UPDATE habits
        SET last_completed_at = latest_logs.max_created_at
        FROM (
            SELECT habit_id, MAX(created_at) AS max_created_at
            FROM habit_logs
            GROUP BY habit_id
        ) AS latest_logs
        WHERE habits.id = latest_logs.habit_id
        """
    )

    op.add_column(
        "users",
        sa.Column(
            "last_daily_summary_sent_for_date",
            sa.Date(),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "last_weekly_summary_sent_for_week_start",
            sa.Date(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "last_weekly_summary_sent_for_week_start")
    op.drop_column("users", "last_daily_summary_sent_for_date")
    op.drop_column("habits", "last_completed_at")
