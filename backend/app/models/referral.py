from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Referral(Base, TimestampMixin):
    """Реферальные начисления."""
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    referrer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    referred_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    challenge_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("user_challenges.id"), nullable=True
    )

    bonus_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 или 2
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    referrer: Mapped["User"] = relationship(
        "User", foreign_keys=[referrer_id], back_populates="referrals_sent"
    )
    referred: Mapped["User"] = relationship(
        "User", foreign_keys=[referred_id], back_populates="referrals_received"
    )

    __table_args__ = (
        Index("ix_referrals_referrer_id", "referrer_id"),
        Index("ix_referrals_referred_id", "referred_id"),
        Index("ix_referrals_paid_at", "paid_at"),
    )

    def __repr__(self) -> str:
        return f"<Referral referrer={self.referrer_id} referred={self.referred_id} level={self.level}>"
