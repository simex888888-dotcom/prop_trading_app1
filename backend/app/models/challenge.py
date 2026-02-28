import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, DateTime, ForeignKey, Index,
    Integer, Numeric, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class DrawdownType(str, enum.Enum):
    static = "static"       # от начального баланса (как FTMO)
    trailing = "trailing"   # от пика equity (как Topstep)


class ChallengeStatus(str, enum.Enum):
    phase1 = "phase1"
    phase2 = "phase2"
    funded = "funded"
    failed = "failed"
    completed = "completed"


class AccountMode(str, enum.Enum):
    demo = "demo"
    funded = "funded"


class ExchangeName(str, enum.Enum):
    bybit = "bybit"
    bingx = "bingx"


class ChallengeType(Base, TimestampMixin):
    """Типы испытаний (планы), настраиваемые в админке."""
    __tablename__ = "challenge_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Визуал карточки
    rank_icon: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    gradient_bg: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Финансовые параметры
    account_size: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Цели
    profit_target_p1: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("8.00")
    )
    profit_target_p2: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("5.00")
    )

    # Лимиты просадки
    max_daily_loss: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("5.00")
    )
    max_total_loss: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("10.00")
    )

    # Торговые дни
    min_trading_days: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    max_trading_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Тип просадки
    drawdown_type: Mapped[DrawdownType] = mapped_column(
        String(16), nullable=False, default=DrawdownType.trailing
    )

    # Дополнительные правила
    consistency_rule: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    news_trading_ban: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Тип испытания
    is_one_phase: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_instant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_refundable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Плечо
    max_leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=50)

    # Режимы аккаунтов
    phase1_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="demo")
    phase2_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="demo")
    funded_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="real")

    # Разделение прибыли (% трейдеру)
    profit_split_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=Decimal("80.00")
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    user_challenges: Mapped[list["UserChallenge"]] = relationship(
        "UserChallenge", back_populates="challenge_type"
    )

    __table_args__ = (
        Index("ix_challenge_types_active", "is_active"),
        Index("ix_challenge_types_account_size", "account_size"),
    )

    def __repr__(self) -> str:
        return f"<ChallengeType id={self.id} name={self.name} size=${self.account_size}>"


class UserChallenge(Base, TimestampMixin):
    """Активные и завершённые испытания пользователей."""
    __tablename__ = "user_challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    challenge_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("challenge_types.id"), nullable=False, index=True
    )

    # Статус и фаза
    status: Mapped[ChallengeStatus] = mapped_column(
        String(16), nullable=False, default=ChallengeStatus.phase1
    )
    phase: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)

    # Режим аккаунта
    account_mode: Mapped[AccountMode] = mapped_column(
        String(16), nullable=False, default=AccountMode.demo
    )

    # Биржа
    exchange: Mapped[ExchangeName] = mapped_column(
        String(16), nullable=False, default=ExchangeName.bybit
    )

    # DEMO аккаунт Bybit (зашифровано AES-256)
    demo_account_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    demo_api_key_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    demo_api_secret_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # REAL аккаунт Bybit (зашифровано AES-256)
    real_account_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    real_api_key_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    real_api_secret_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Финансовые показатели
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    peak_equity: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    daily_start_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    daily_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )
    total_pnl: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0.00")
    )

    # Торговые дни
    trading_days_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Даты событий
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    funded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Дата сброса дневного баланса
    daily_reset_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="challenges")
    challenge_type: Mapped["ChallengeType"] = relationship(
        "ChallengeType", back_populates="user_challenges"
    )
    trades: Mapped[list["Trade"]] = relationship(
        "Trade", back_populates="challenge", cascade="all, delete-orphan"
    )
    violations: Mapped[list["Violation"]] = relationship(
        "Violation", back_populates="challenge", cascade="all, delete-orphan"
    )
    payouts: Mapped[list["Payout"]] = relationship(
        "Payout", back_populates="challenge"
    )
    scaling_steps: Mapped[list["ScalingStep"]] = relationship(
        "ScalingStep", back_populates="challenge", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_user_challenges_user_id", "user_id"),
        Index("ix_user_challenges_status", "status"),
        Index("ix_user_challenges_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<UserChallenge id={self.id} user_id={self.user_id} status={self.status}>"
