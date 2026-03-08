"""
PaperPosition — симуляционная позиция (paper trading).
Позволяет торговать внутри приложения без реального Bybit аккаунта.
"""
import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class PaperSide(str, enum.Enum):
    Buy = "Buy"
    Sell = "Sell"


class PaperPosition(Base, TimestampMixin):
    """Симуляционная (paper) позиция трейдера."""
    __tablename__ = "paper_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    side: Mapped[PaperSide] = mapped_column(String(8), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    take_profit: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    stop_loss: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)

    # Set when closed
    exit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 8), nullable=True)
    pnl: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    pnl_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4), nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Virtual paper balance snapshot on open (collateral used)
    margin_used: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))

    user: Mapped["User"] = relationship("User", back_populates="paper_positions")

    __table_args__ = (
        Index("ix_paper_positions_user_id", "user_id"),
        Index("ix_paper_positions_is_closed", "is_closed"),
    )

    def __repr__(self) -> str:
        return f"<PaperPosition id={self.id} symbol={self.symbol} side={self.side} closed={self.is_closed}>"
