import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class PayoutStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    processing = "processing"
    sent = "sent"


class PayoutNetwork(str, enum.Enum):
    trc20 = "TRC20"
    erc20 = "ERC20"
    bep20 = "BEP20"


class Payout(Base, TimestampMixin):
    """Запросы на выплату прибыли."""
    __tablename__ = "payouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_challenges.id"), nullable=False, index=True
    )

    # Суммы
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, default=Decimal("0"))
    net_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)

    # Реквизиты
    wallet_address: Mapped[str] = mapped_column(String(256), nullable=False)
    network: Mapped[PayoutNetwork] = mapped_column(String(8), nullable=False)

    # Статус
    status: Mapped[PayoutStatus] = mapped_column(
        String(16), nullable=False, default=PayoutStatus.pending
    )

    # Временные метки
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tx_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # Причина отклонения
    reject_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="payouts")
    challenge: Mapped["UserChallenge"] = relationship("UserChallenge", back_populates="payouts")

    __table_args__ = (
        Index("ix_payouts_user_id", "user_id"),
        Index("ix_payouts_status", "status"),
        Index("ix_payouts_challenge_id", "challenge_id"),
    )

    def __repr__(self) -> str:
        return f"<Payout id={self.id} amount={self.net_amount} status={self.status}>"
