"""
/referral — реферальная программа.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.referral import Referral
from app.models.user import User
from app.schemas.common import APIResponse

router = APIRouter(prefix="/referral", tags=["referral"])


class ReferralInfoOut(BaseModel):
    referral_code: str
    referral_link: str
    total_referrals: int
    level1_count: int
    level2_count: int
    total_earned: float
    pending_payout: float


class ReferralEarningOut(BaseModel):
    id: int
    referred_username: Optional[str]
    bonus_amount: float
    level: int
    paid: bool
    paid_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("/info", response_model=APIResponse[ReferralInfoOut])
async def get_referral_info(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[ReferralInfoOut]:
    """Реферальная ссылка и статистика."""
    referral_link = (
        f"https://t.me/{settings.telegram_bot_username}"
        f"?start={user.referral_code}"
    )

    # Подсчёт рефералов
    l1_result = await session.execute(
        select(func.count(Referral.id)).where(
            Referral.referrer_id == user.id, Referral.level == 1
        )
    )
    l1_count = l1_result.scalar() or 0

    l2_result = await session.execute(
        select(func.count(Referral.id)).where(
            Referral.referrer_id == user.id, Referral.level == 2
        )
    )
    l2_count = l2_result.scalar() or 0

    # Суммы
    earned_result = await session.execute(
        select(func.sum(Referral.bonus_amount)).where(
            Referral.referrer_id == user.id,
            Referral.paid_at.isnot(None),
        )
    )
    total_earned = float(earned_result.scalar() or 0)

    pending_result = await session.execute(
        select(func.sum(Referral.bonus_amount)).where(
            Referral.referrer_id == user.id,
            Referral.paid_at.is_(None),
        )
    )
    pending = float(pending_result.scalar() or 0)

    return APIResponse(data=ReferralInfoOut(
        referral_code=user.referral_code,
        referral_link=referral_link,
        total_referrals=l1_count + l2_count,
        level1_count=l1_count,
        level2_count=l2_count,
        total_earned=round(total_earned, 2),
        pending_payout=round(pending, 2),
    ))


@router.get("/earnings", response_model=APIResponse[list[ReferralEarningOut]])
async def get_referral_earnings(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[ReferralEarningOut]]:
    """Список реферальных начислений."""
    result = await session.execute(
        select(Referral, User)
        .join(User, Referral.referred_id == User.id)
        .where(Referral.referrer_id == user.id)
        .order_by(Referral.created_at.desc())
    )
    rows = result.all()

    return APIResponse(data=[
        ReferralEarningOut(
            id=ref.id,
            referred_username=referred_user.username,
            bonus_amount=float(ref.bonus_amount),
            level=ref.level,
            paid=ref.paid_at is not None,
            paid_at=ref.paid_at,
            created_at=ref.created_at,
        )
        for ref, referred_user in rows
    ])
