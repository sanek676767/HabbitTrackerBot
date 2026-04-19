"""Add user last interaction timestamp

Revision ID: 0013_user_last_interaction
Revises: 0012_add_habit_pause_state
Create Date: 2026-04-19 22:50:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0013_user_last_interaction"
down_revision: Union[str, None] = "0012_add_habit_pause_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("last_interaction_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "last_interaction_at")
