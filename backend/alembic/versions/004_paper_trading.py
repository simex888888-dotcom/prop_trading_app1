"""004 paper trading

Revision ID: 004_paper_trading
Revises: 003_add_pending_payment_and_username
Create Date: 2026-03-07 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "004_paper_trading"
down_revision = "003_add_pending_payment_and_username"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_positions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("side", sa.String(8), nullable=False),
        sa.Column("qty", sa.Numeric(18, 8), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("leverage", sa.Integer(), nullable=False, default=1),
        sa.Column("take_profit", sa.Numeric(18, 8), nullable=True),
        sa.Column("stop_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("exit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("pnl", sa.Numeric(18, 2), nullable=True),
        sa.Column("pnl_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("is_closed", sa.Boolean(), nullable=False, default=False),
        sa.Column("margin_used", sa.Numeric(18, 2), nullable=False, default=0),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_paper_positions_user_id", "paper_positions", ["user_id"])
    op.create_index("ix_paper_positions_is_closed", "paper_positions", ["is_closed"])


def downgrade() -> None:
    op.drop_index("ix_paper_positions_is_closed", "paper_positions")
    op.drop_index("ix_paper_positions_user_id", "paper_positions")
    op.drop_table("paper_positions")
