"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(64), nullable=False),
        sa.Column("last_name", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phase", sa.Enum("EVALUATION", "VERIFICATION", "FUNDED", name="accountphase"), nullable=False, server_default="EVALUATION"),
        sa.Column("status", sa.Enum("ACTIVE", "PASSED", "FAILED", name="accountstatus"), nullable=False, server_default="ACTIVE"),
        sa.Column("initial_balance", sa.Numeric(18, 2), nullable=False, server_default="10000.00"),
        sa.Column("current_balance", sa.Numeric(18, 2), nullable=False, server_default="10000.00"),
        sa.Column("peak_equity", sa.Numeric(18, 2), nullable=False, server_default="10000.00"),
        sa.Column("day_start_balance", sa.Numeric(18, 2), nullable=False, server_default="10000.00"),
        sa.Column("day_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_daily_drawdown_pct", sa.Numeric(5, 2), nullable=False, server_default="5.00"),
        sa.Column("max_trailing_drawdown_pct", sa.Numeric(5, 2), nullable=False, server_default="10.00"),
        sa.Column("profit_target_pct", sa.Numeric(5, 2), nullable=False, server_default="8.00"),
        sa.Column("min_trading_days", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("trading_days_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("winning_trades", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("profit_split_pct", sa.Numeric(5, 2), nullable=False, server_default="80.00"),
        sa.Column("fail_reason", sa.Enum("DAILY_DRAWDOWN_EXCEEDED", "TRAILING_DRAWDOWN_EXCEEDED", name="failreason"), nullable=True),
        sa.Column("fail_detail", sa.Text(), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phase_passed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])
    op.create_index("ix_accounts_status", "accounts", ["status"])

    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("symbol", sa.String(20), nullable=False),
        sa.Column("direction", sa.Enum("LONG", "SHORT", name="tradedirection"), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "CLOSED", name="tradestatus"), nullable=False, server_default="OPEN"),
        sa.Column("leverage", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("position_size", sa.Numeric(18, 8), nullable=False),
        sa.Column("notional_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("margin_used", sa.Numeric(18, 2), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("take_profit", sa.Numeric(18, 8), nullable=False),
        sa.Column("stop_loss", sa.Numeric(18, 8), nullable=False),
        sa.Column("close_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("realized_pnl", sa.Numeric(18, 2), nullable=True),
        sa.Column("close_reason", sa.Enum("MANUAL", "TAKE_PROFIT", "STOP_LOSS", "DAILY_DRAWDOWN", "TRAILING_DRAWDOWN", name="closereason"), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_trades_account_id", "trades", ["account_id"])
    op.create_index("ix_trades_status", "trades", ["status"])
    op.create_index("ix_trades_symbol", "trades", ["symbol"])

    op.create_table(
        "daily_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("equity", sa.Numeric(18, 2), nullable=False),
        sa.Column("balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("trades_closed", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_daily_snapshots_account_date", "daily_snapshots", ["account_id", "snapshot_date"])


def downgrade() -> None:
    op.drop_table("daily_snapshots")
    op.drop_table("trades")
    op.drop_table("accounts")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS closereason")
    op.execute("DROP TYPE IF EXISTS tradestatus")
    op.execute("DROP TYPE IF EXISTS tradedirection")
    op.execute("DROP TYPE IF EXISTS failreason")
    op.execute("DROP TYPE IF EXISTS accountstatus")
    op.execute("DROP TYPE IF EXISTS accountphase")
