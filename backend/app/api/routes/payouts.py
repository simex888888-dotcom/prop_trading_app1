"""
/payouts — выплаты для funded трейдеров.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.challenge import ChallengeStatus, UserChallenge
from app.models.payout import Payout, PayoutNetwork, PayoutStatus
from app.models.user import User, UserRole
from app.schemas.common import APIResponse

router = APIRouter(prefix="/payouts", tags=["payouts"])


class PayoutOut(BaseModel):
    id: int
    challenge_id: int
    amount: float
    fee: float
    net_amount: float
    wallet_address: str
    network: str
    status: str
    requested_at: datetime
    processed_at: Optional[datetime]
    tx_hash: Optional[str]

    model_config = {"from_attributes": True}


class PayoutRequest(BaseModel):
    challenge_id: int
    amount: float
    wallet_address: str
    network: str

    @field_validator("network")
    @classmethod
    def validate_network(cls, v: str) -> str:
        allowed = [n.value for n in PayoutNetwork]
        if v not in allowed:
            raise ValueError(f"Network must be one of: {allowed}")
        return v

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet(cls, v: str) -> str:
        if len(v) < 10:
            raise ValueError("Invalid wallet address")
        return v.strip()


class AvailablePayoutOut(BaseModel):
    challenge_id: int
    available_amount: float
    profit_split_pct: float
    min_payout: float
    can_request: bool
    pending_payout: bool


@router.get("", response_model=APIResponse[list[PayoutOut]])
async def get_payouts(
    challenge_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[PayoutOut]]:
    """История выплат пользователя."""
    stmt = select(Payout).where(Payout.user_id == user.id)
    if challenge_id:
        stmt = stmt.where(Payout.challenge_id == challenge_id)
    stmt = stmt.order_by(Payout.requested_at.desc())
    result = await session.execute(stmt)
    payouts = result.scalars().all()
    return APIResponse(data=[PayoutOut.model_validate(p) for p in payouts])


@router.get("/available", response_model=APIResponse[AvailablePayoutOut])
async def get_available_payout(
    challenge_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[AvailablePayoutOut]:
    """Доступная сумма к выплате для funded аккаунта."""
    if user.role not in [UserRole.funded_trader, UserRole.elite_trader, UserRole.admin, UserRole.super_admin]:
        raise HTTPException(status_code=403, detail="Only funded traders can request payouts")

    result = await session.execute(
        select(UserChallenge)
        .where(
            UserChallenge.id == challenge_id,
            UserChallenge.user_id == user.id,
            UserChallenge.status == ChallengeStatus.funded,
        )
        .options(selectinload(UserChallenge.challenge_type))
    )
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Funded challenge not found")

    ct = challenge.challenge_type
    total_pnl = float(challenge.total_pnl)
    split_pct = float(ct.profit_split_pct)

    # Трейдер получает profit_split_pct% от прибыли
    available = (total_pnl * split_pct / 100) if total_pnl > 0 else 0.0

    # Вычитаем уже выплаченное
    paid_result = await session.execute(
        select(Payout)
        .where(
            Payout.challenge_id == challenge_id,
            Payout.status.in_([PayoutStatus.approved, PayoutStatus.sent]),
        )
    )
    paid_payouts = paid_result.scalars().all()
    already_paid = sum(float(p.net_amount) for p in paid_payouts)
    available = max(0, available - already_paid)

    # Есть ли ожидающие выплаты
    pending_result = await session.execute(
        select(Payout).where(
            Payout.challenge_id == challenge_id,
            Payout.status == PayoutStatus.pending,
        )
    )
    has_pending = pending_result.scalar_one_or_none() is not None

    return APIResponse(data=AvailablePayoutOut(
        challenge_id=challenge_id,
        available_amount=round(available, 2),
        profit_split_pct=split_pct,
        min_payout=settings.min_payout_amount,
        can_request=available >= settings.min_payout_amount and not has_pending,
        pending_payout=has_pending,
    ))


@router.post("/request", response_model=APIResponse[PayoutOut])
async def request_payout(
    body: PayoutRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[PayoutOut]:
    """Запрос на выплату прибыли."""
    if user.role not in [UserRole.funded_trader, UserRole.elite_trader, UserRole.admin, UserRole.super_admin]:
        raise HTTPException(status_code=403, detail="Only funded traders can request payouts")

    if body.amount < settings.min_payout_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum payout amount is ${settings.min_payout_amount}"
        )

    # Проверяем доступность
    available_resp = await get_available_payout(challenge_id=body.challenge_id, user=user, session=session)
    available = available_resp.data
    if not available.can_request:
        raise HTTPException(status_code=400, detail="Cannot request payout now")
    if body.amount > available.available_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Amount exceeds available balance ({available.available_amount:.2f})"
        )

    now = datetime.now(timezone.utc)
    fee = Decimal("0")  # Комиссия можно добавить позже
    net_amount = Decimal(str(body.amount)) - fee

    payout = Payout(
        user_id=user.id,
        challenge_id=body.challenge_id,
        amount=Decimal(str(body.amount)),
        fee=fee,
        net_amount=net_amount,
        wallet_address=body.wallet_address,
        network=body.network,
        status=PayoutStatus.pending,
        requested_at=now,
    )
    session.add(payout)
    await session.commit()

    return APIResponse(data=PayoutOut.model_validate(payout))
