"""005 bybit testnet support

Добавляет поле demo_account_username в user_challenges для хранения
username суб-аккаунта на Bybit Testnet (используется при переходе на testnet).

Revision ID: 005_bybit_testnet
Revises: 004_paper_trading
Create Date: 2026-03-08 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "005_bybit_testnet"
down_revision = "004_paper_trading"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем username суб-аккаунта (для testnet и real аккаунтов)
    op.add_column(
        "user_challenges",
        sa.Column("demo_account_username", sa.String(128), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_challenges", "demo_account_username")
