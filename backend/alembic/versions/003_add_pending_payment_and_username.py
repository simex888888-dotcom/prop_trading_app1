"""add pending_payment status and demo_account_username column

Revision ID: 003_pending_payment
Revises: 002_seed_data
Create Date: 2026-03-05
"""
from alembic import op
import sqlalchemy as sa

revision = "003_pending_payment"
down_revision = "002_seed_data"
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
