import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, Integer,
    Numeric, String, Text, ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class AccountPhase(str, enum.Enum):
    EVALUATION = "EVALUATION"
    VERIFICATION = "VERIFICATION"
    FUNDED = "FUNDED"


class AccountStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PASSED = "PASSED"
    FAILED = "FAILED"


class TradeDirection(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class TradeStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class CloseReason(str, enum.Enum):
    MANUAL = "MANUAL"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    DAILY_DRAWDOWN = "DAILY_DRAWDOWN"
    TRAILING_DRAWDOWN = "TRAILING_DRAWDOWN"


class FailReason(str, enum.Enum):
    DAILY_DRAWDOWN_EXCEEDED = "DAILY_DRAWDOWN_EXCEEDED"
    TRAILING_DRAWDOWN_EXCEEDED = "TRAILING_DRAWDOWN_EXCEEDED"


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True)  # Telegram user_id
    username = Column(String(64), nullable=True)
    first_name = Column(String(64), nullable=False)
    last_name = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    accounts = relationship("Account", back_populates="user", cascade="all, delete-orphan")


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    phase = Column(Enum(AccountPhase), nullable=False, default=AccountPhase.EVALUATION)
    status = Column(Enum(AccountStatus), nullable=False, default=AccountStatus.ACTIVE)

    initial_balance = Column(Numeric(18, 2), nullable=False, default=Decimal("10000.00"))
    current_balance = Column(Numeric(18, 2), nullable=False, default=Decimal("10000.00"))
    peak_equity = Column(Numeric(18, 2), nullable=False, default=Decimal("10000.00"))

    # Баланс на начало текущего торгового дня (UTC)
    day_start_balance = Column(Numeric(18, 2), nullable=False, default=Decimal("10000.00"))
    day_start_date = Column(DateTime(timezone=True), nullable=True)

    max_daily_drawdown_pct = Column(Numeric(5, 2), nullable=False, default=Decimal("5.00"))
    max_trailing_drawdown_pct = Column(Numeric(5, 2), nullable=False, default=Decimal("10.00"))
    profit_target_pct = Column(Numeric(5, 2), nullable=False, default=Decimal("8.00"))
    min_trading_days = Column(Integer, nullable=False, default=5)

    trading_days_count = Column(Integer, nullable=False, default=0)
    total_trades = Column(Integer, nullable=False, default=0)
    winning_trades = Column(Integer, nullable=False, default=0)
    profit_split_pct = Column(Numeric(5, 2), nullable=False, default=Decimal("80.00"))

    fail_reason = Column(Enum(FailReason), nullable=True)
    fail_detail = Column(Text, nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)

    phase_passed_at = Column(DateTime(timezone=True), nullable=True)
    attempt_number = Column(Integer, nullable=False, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="accounts")
    trades = relationship("Trade", back_populates="account", cascade="all, delete-orphan")
    daily_snapshots = relationship("DailySnapshot", back_populates="account", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_accounts_user_id", "user_id"),
        Index("ix_accounts_status", "status"),
    )


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)

    symbol = Column(String(20), nullable=False)  # e.g. BTCUSDT
    direction = Column(Enum(TradeDirection), nullable=False)
    status = Column(Enum(TradeStatus), nullable=False, default=TradeStatus.OPEN)

    leverage = Column(Integer, nullable=False, default=1)
    # Размер позиции в базовой валюте (BTC, ETH и т.д.)
    position_size = Column(Numeric(18, 8), nullable=False)
    # Размер в USDT (position_size * entry_price)
    notional_value = Column(Numeric(18, 2), nullable=False)
    # Маржа = notional_value / leverage
    margin_used = Column(Numeric(18, 2), nullable=False)

    entry_price = Column(Numeric(18, 8), nullable=False)
    take_profit = Column(Numeric(18, 8), nullable=False)
    stop_loss = Column(Numeric(18, 8), nullable=False)

    close_price = Column(Numeric(18, 8), nullable=True)
    realized_pnl = Column(Numeric(18, 2), nullable=True)
    close_reason = Column(Enum(CloseReason), nullable=True)

    opened_at = Column(DateTime(timezone=True), server_default=func.now())
    closed_at = Column(DateTime(timezone=True), nullable=True)

    account = relationship("Account", back_populates="trades")

    __table_args__ = (
        Index("ix_trades_account_id", "account_id"),
        Index("ix_trades_status", "status"),
        Index("ix_trades_symbol", "symbol"),
    )


class DailySnapshot(Base):
    """Снэпшот equity на конец каждого торгового дня для расчёта статистики."""
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    snapshot_date = Column(DateTime(timezone=True), nullable=False)
    equity = Column(Numeric(18, 2), nullable=False)
    balance = Column(Numeric(18, 2), nullable=False)
    trades_closed = Column(Integer, nullable=False, default=0)

    account = relationship("Account", back_populates="daily_snapshots")

    __table_args__ = (
        Index("ix_daily_snapshots_account_date", "account_id", "snapshot_date"),
    )
