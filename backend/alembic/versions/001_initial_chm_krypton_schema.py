"""Initial CHM_KRYPTON schema

Revision ID: 001_initial
Revises:
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(64), nullable=True),
        sa.Column("first_name", sa.String(128), nullable=False),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("role", sa.String(32), nullable=False, server_default="guest"),
        sa.Column("referral_code", sa.String(16), nullable=False),
        sa.Column("referred_by", sa.BigInteger(), nullable=True),
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=True)
    op.create_index("ix_users_referral_code", "users", ["referral_code"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_referred_by", "users", ["referred_by"])

    # ── challenge_types ────────────────────────────────────────────────────────
    op.create_table(
        "challenge_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rank_icon", sa.String(256), nullable=True),
        sa.Column("gradient_bg", sa.String(128), nullable=True),
        sa.Column("account_size", sa.Numeric(18, 2), nullable=False),
        sa.Column("price", sa.Numeric(18, 2), nullable=False),
        sa.Column("profit_target_p1", sa.Numeric(5, 2), nullable=False, server_default="8.00"),
        sa.Column("profit_target_p2", sa.Numeric(5, 2), nullable=False, server_default="5.00"),
        sa.Column("max_daily_loss", sa.Numeric(5, 2), nullable=False, server_default="5.00"),
        sa.Column("max_total_loss", sa.Numeric(5, 2), nullable=False, server_default="10.00"),
        sa.Column("min_trading_days", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("max_trading_days", sa.Integer(), nullable=True),
        sa.Column("drawdown_type", sa.String(16), nullable=False, server_default="trailing"),
        sa.Column("consistency_rule", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("news_trading_ban", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_one_phase", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_instant", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_refundable", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("max_leverage", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("phase1_mode", sa.String(16), nullable=False, server_default="demo"),
        sa.Column("phase2_mode", sa.String(16), nullable=False, server_default="demo"),
        sa.Column("funded_mode", sa.String(16), nullable=False, server_default="real"),
        sa.Column("profit_split_pct", sa.Numeric(5, 2), nullable=False, server_default="80.00"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_challenge_types_active", "challenge_types", ["is_active"])
    op.create_index("ix_challenge_types_account_size", "challenge_types", ["account_size"])

    # ── user_challenges ────────────────────────────────────────────────────────
    op.create_table(
        "user_challenges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("challenge_type_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="phase1"),
        sa.Column("phase", sa.Integer(), nullable=True, server_default="1"),
        sa.Column("account_mode", sa.String(16), nullable=False, server_default="demo"),
        sa.Column("exchange", sa.String(16), nullable=False, server_default="bybit"),
        sa.Column("demo_account_id", sa.String(128), nullable=True),
        sa.Column("demo_api_key_enc", sa.Text(), nullable=True),
        sa.Column("demo_api_secret_enc", sa.Text(), nullable=True),
        sa.Column("real_account_id", sa.String(128), nullable=True),
        sa.Column("real_api_key_enc", sa.Text(), nullable=True),
        sa.Column("real_api_secret_enc", sa.Text(), nullable=True),
        sa.Column("initial_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("current_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("peak_equity", sa.Numeric(18, 2), nullable=False),
        sa.Column("daily_start_balance", sa.Numeric(18, 2), nullable=False),
        sa.Column("daily_pnl", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("total_pnl", sa.Numeric(18, 2), nullable=False, server_default="0.00"),
        sa.Column("trading_days_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_reason", sa.Text(), nullable=True),
        sa.Column("funded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("daily_reset_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_type_id"], ["challenge_types.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_challenges_user_id", "user_challenges", ["user_id"])
    op.create_index("ix_user_challenges_status", "user_challenges", ["status"])
    op.create_index(
        "ix_user_challenges_user_status", "user_challenges", ["user_id", "status"]
    )

    # ── trades ─────────────────────────────────────────────────────────────────
    op.create_table(
        "trades",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("exchange_order_id", sa.String(128), nullable=True),
        sa.Column("symbol", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 8), nullable=False),
        sa.Column("exit_price", sa.Numeric(18, 8), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 8), nullable=False),
        sa.Column("leverage", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("pnl", sa.Numeric(18, 2), nullable=True),
        sa.Column("pnl_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["user_challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trades_challenge_id", "trades", ["challenge_id"])
    op.create_index("ix_trades_symbol", "trades", ["symbol"])
    op.create_index("ix_trades_opened_at", "trades", ["opened_at"])
    op.create_index("ix_trades_closed_at", "trades", ["closed_at"])

    # ── violations ─────────────────────────────────────────────────────────────
    op.create_table(
        "violations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("value", sa.Numeric(18, 4), nullable=False),
        sa.Column("limit_value", sa.Numeric(18, 4), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["user_challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_violations_challenge_id", "violations", ["challenge_id"])
    op.create_index("ix_violations_type", "violations", ["type"])

    # ── payouts ────────────────────────────────────────────────────────────────
    op.create_table(
        "payouts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("fee", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("net_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("wallet_address", sa.String(256), nullable=False),
        sa.Column("network", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tx_hash", sa.String(128), nullable=True),
        sa.Column("reject_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_id"], ["user_challenges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payouts_user_id", "payouts", ["user_id"])
    op.create_index("ix_payouts_status", "payouts", ["status"])
    op.create_index("ix_payouts_challenge_id", "payouts", ["challenge_id"])

    # ── achievements ───────────────────────────────────────────────────────────
    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("name_ru", sa.String(128), nullable=False),
        sa.Column("description_ru", sa.Text(), nullable=False),
        sa.Column("lottie_file", sa.String(256), nullable=True),
        sa.Column("levels_config", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_achievements_key", "achievements", ["key"], unique=True)

    # ── user_achievements ──────────────────────────────────────────────────────
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("achievement_id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(16), nullable=False, server_default="locked"),
        sa.Column("progress", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("unlocked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["achievement_id"], ["achievements.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_achievements_user_id", "user_achievements", ["user_id"])
    op.create_index(
        "ix_user_achievements_user_achievement",
        "user_achievements",
        ["user_id", "achievement_id"],
    )

    # ── referrals ──────────────────────────────────────────────────────────────
    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("referrer_id", sa.BigInteger(), nullable=False),
        sa.Column("referred_id", sa.BigInteger(), nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=True),
        sa.Column("bonus_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["referrer_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["referred_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["challenge_id"], ["user_challenges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_referrals_referrer_id", "referrals", ["referrer_id"])
    op.create_index("ix_referrals_referred_id", "referrals", ["referred_id"])
    op.create_index("ix_referrals_paid_at", "referrals", ["paid_at"])

    # ── notifications ──────────────────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    # ── scaling_steps ──────────────────────────────────────────────────────────
    op.create_table(
        "scaling_steps",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("challenge_id", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("account_size_before", sa.Numeric(18, 2), nullable=False),
        sa.Column("account_size_after", sa.Numeric(18, 2), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["challenge_id"], ["user_challenges.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scaling_steps_challenge_id", "scaling_steps", ["challenge_id"])


def downgrade() -> None:
    op.drop_table("scaling_steps")
    op.drop_table("notifications")
    op.drop_table("referrals")
    op.drop_table("user_achievements")
    op.drop_table("achievements")
    op.drop_table("payouts")
    op.drop_table("violations")
    op.drop_table("trades")
    op.drop_table("user_challenges")
    op.drop_table("challenge_types")
    op.drop_table("users")
