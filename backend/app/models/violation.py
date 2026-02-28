import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ViolationType(str, enum.Enum):
    daily_loss = "daily_loss"
    total_loss = "total_loss"
    consistency = "consistency"
    news_ban = "news_ban"
    max_trading_days = "max_trading_days"
    self_hedging = "self_hedging"
    custom = "custom"


class Violation(Base):
    """Нарушения правил испытания."""
    __tablename__ = "violations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_challenges.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    type: Mapped[ViolationType] = mapped_column(String(32), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    limit_value: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationship
    challenge: Mapped["UserChallenge"] = relationship("UserChallenge", back_populates="violations")

    __table_args__ = (
        Index("ix_violations_challenge_id", "challenge_id"),
        Index("ix_violations_type", "type"),
    )

    def __repr__(self) -> str:
        return f"<Violation id={self.id} type={self.type} challenge_id={self.challenge_id}>"
