"""add pending_payment status and demo_account_username column

Revision ID: 003
Revises: 002
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add demo_account_username column (nullable — existing rows don't have it)
    op.add_column(
        "user_challenges",
        sa.Column("demo_account_username", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_challenges", "demo_account_username")
