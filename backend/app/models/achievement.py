from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin


class Achievement(Base, TimestampMixin):
    """Справочник достижений платформы."""
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    name_ru: Mapped[str] = mapped_column(String(128), nullable=False)
    description_ru: Mapped[str] = mapped_column(Text, nullable=False)
    lottie_file: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # JSON структура: {"bronze": 1, "silver": 5, "gold": 10, "platinum": 25}
    levels_config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # Relationships
    user_achievements: Mapped[list["UserAchievement"]] = relationship(
        "UserAchievement", back_populates="achievement"
    )

    def __repr__(self) -> str:
        return f"<Achievement key={self.key} name={self.name_ru}>"


class AchievementLevel(str):
    locked = "locked"
    bronze = "bronze"
    silver = "silver"
    gold = "gold"
    platinum = "platinum"


class UserAchievement(Base):
    """Достижения конкретного пользователя."""
    __tablename__ = "user_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    achievement_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("achievements.id"), nullable=False, index=True
    )

    level: Mapped[str] = mapped_column(String(16), nullable=False, default="locked")
    progress: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0"))
    unlocked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="achievements")
    achievement: Mapped["Achievement"] = relationship("Achievement", back_populates="user_achievements")

    __table_args__ = (
        Index("ix_user_achievements_user_id", "user_id"),
        Index("ix_user_achievements_user_achievement", "user_id", "achievement_id"),
    )

    def __repr__(self) -> str:
        return f"<UserAchievement user_id={self.user_id} achievement_id={self.achievement_id} level={self.level}>"
