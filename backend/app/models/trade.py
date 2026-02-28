import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class TradeDirection(str, enum.Enum):
    long = "long"
    short = "short"


class Trade(Base, TimestampMixin):
    """История закрытых сделок трейдера."""
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_challenges.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Идентификатор на бирже
    exchange_order_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Параметры сделки
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    direction: Mapped[TradeDirection] = mapped_column(String(8), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # PnL
    pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    pnl_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)

    # Временные метки
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    challenge: Mapped["UserChallenge"] = relationship("UserChallenge", back_populates="trades")

    __table_args__ = (
        Index("ix_trades_challenge_id", "challenge_id"),
        Index("ix_trades_symbol", "symbol"),
        Index("ix_trades_opened_at", "opened_at"),
        Index("ix_trades_closed_at", "closed_at"),
    )

    def __repr__(self) -> str:
        return f"<Trade id={self.id} symbol={self.symbol} direction={self.direction} pnl={self.pnl}>"
