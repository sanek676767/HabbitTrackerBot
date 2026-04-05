"""Add admin action logs

Revision ID: 0010_add_admin_action_logs
Revises: 0009_add_habit_schedules
Create Date: 2026-04-05 23:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0010_add_admin_action_logs"
down_revision: Union[str, None] = "0009_add_habit_schedules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "admin_action_logs",
        sa.Column("actor_user_id", sa.BigInteger(), nullable=False),
        sa.Column("target_user_id", sa.BigInteger(), nullable=True),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column(
            "id",
            sa.BigInteger(),
            sa.Identity(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name=op.f("fk_admin_action_logs_actor_user_id_users")),
        sa.ForeignKeyConstraint(
            ["target_user_id"],
            ["users.id"],
            name=op.f("fk_admin_action_logs_target_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_admin_action_logs")),
    )
    op.create_index(
        "ix_admin_action_logs_created_at",
        "admin_action_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_action_logs_actor_user_id_created_at",
        "admin_action_logs",
        ["actor_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_action_logs_target_user_id_created_at",
        "admin_action_logs",
        ["target_user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_action_logs_target_user_id_created_at", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_actor_user_id_created_at", table_name="admin_action_logs")
    op.drop_index("ix_admin_action_logs_created_at", table_name="admin_action_logs")
    op.drop_table("admin_action_logs")
