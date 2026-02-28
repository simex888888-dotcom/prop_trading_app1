from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScalingStep(Base):
    """История масштабирования счёта трейдера."""
    __tablename__ = "scaling_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    challenge_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user_challenges.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    account_size_before: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    account_size_after: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationship
    challenge: Mapped["UserChallenge"] = relationship("UserChallenge", back_populates="scaling_steps")

    __table_args__ = (
        Index("ix_scaling_steps_challenge_id", "challenge_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<ScalingStep challenge={self.challenge_id} "
            f"step={self.step_number} "
            f"{self.account_size_before}→{self.account_size_after}>"
        )
