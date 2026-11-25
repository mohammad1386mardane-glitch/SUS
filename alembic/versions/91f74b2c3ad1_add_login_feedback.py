"""add persistent login feedback

Revision ID: 91f74b2c3ad1
Revises: 8b7a08acf8dc
Create Date: 2026-11-25 20:16:38.557000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91f74b2c3ad1"
down_revision: str | Sequence[str] | None = "8b7a08acf8dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "login_events",
        sa.Column("event_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "uq_login_events_event_id",
        "login_events",
        ["event_id"],
        unique=True,
    )
    op.create_table(
        "login_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("login_event_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "label IN ('real_attack', 'false_positive')",
            name="ck_login_feedback_label",
        ),
        sa.ForeignKeyConstraint(
            ["login_event_id"],
            ["login_events.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "login_event_id",
            name="uq_login_feedback_login_event_id",
        ),
    )


def downgrade() -> None:
    op.drop_table("login_feedback")
    op.drop_index("uq_login_events_event_id", table_name="login_events")
    op.drop_column("login_events", "event_id")
