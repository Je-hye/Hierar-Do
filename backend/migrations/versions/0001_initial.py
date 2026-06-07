"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-05-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("deadline", sa.Date(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "active", "done", name="goalstatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("available_hours_weekday", sa.Integer(), nullable=True),
        sa.Column("available_hours_weekend", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "milestones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("goal_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "active", "done", name="milestonestatus", native_enum=False),
            nullable=False,
        ),
        sa.Column("suggested_by_ai", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["goal_id"], ["goals.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "todos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("milestone_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("is_done", sa.Boolean(), nullable=False),
        sa.Column("suggested_by_ai", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["milestone_id"], ["milestones.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("todos")
    op.drop_table("milestones")
    op.drop_table("goals")
    op.drop_table("users")
