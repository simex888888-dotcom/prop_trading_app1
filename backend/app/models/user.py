import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class UserRole(str, enum.Enum):
    guest = "guest"
    challenger = "challenger"
    funded_trader = "funded_trader"
    elite_trader = "elite_trader"
    admin = "admin"
    super_admin = "super_admin"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    role: Mapped[UserRole] = mapped_column(
        String(32), nullable=False, default=UserRole.guest
    )

    referral_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    referred_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True, index=True
    )

    streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_active_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    challenges: Mapped[list["UserChallenge"]] = relationship(
        "UserChallenge", back_populates="user", cascade="all, delete-orphan"
    )
    achievements: Mapped[list["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    payouts: Mapped[list["Payout"]] = relationship(
        "Payout", back_populates="user"
    )
    referrals_sent: Mapped[list["Referral"]] = relationship(
        "Referral", foreign_keys="Referral.referrer_id", back_populates="referrer"
    )
    referrals_received: Mapped[list["Referral"]] = relationship(
        "Referral", foreign_keys="Referral.referred_id", back_populates="referred"
    )

    __table_args__ = (
        Index("ix_users_telegram_id", "telegram_id"),
        Index("ix_users_referral_code", "referral_code"),
        Index("ix_users_role", "role"),
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} telegram_id={self.telegram_id} role={self.role}>"
