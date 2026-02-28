"""
/admin — административные эндпоинты (только admin/super_admin).
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_admin, require_super_admin
from app.core.database import get_db
from app.models.challenge import ChallengeStatus, ChallengeType, UserChallenge
from app.models.payout import Payout, PayoutStatus
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, PaginatedResponse

router = APIRouter(prefix="/admin", tags=["admin"])


# ─── Схемы ────────────────────────────────────────────────────────────────────

class UserAdminOut(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    first_name: str
    role: str
    referral_code: str
    streak_days: int
    is_blocked: bool
    created_at: datetime
    active_challenges: int

    model_config = {"from_attributes": True}


class ChallengeAdminOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str]
    challenge_type_name: str
    account_size: float
    status: str
    phase: Optional[int]
    account_mode: str
    total_pnl: float
    daily_pnl: float
    trading_days_count: int
    started_at: Optional[datetime]
    failed_reason: Optional[str]


class PayoutAdminOut(BaseModel):
    id: int
    user_id: int
    username: Optional[str]
    challenge_id: int
    amount: float
    net_amount: float
    wallet_address: str
    network: str
    status: str
    requested_at: datetime
    processed_at: Optional[datetime]
    reject_reason: Optional[str]


class OverviewOut(BaseModel):
    total_users: int
    active_challengers: int
    active_funded: int
    pending_payouts: int
    pending_payout_amount: float
    total_revenue: float
    challenges_passed_total: int
    challenges_failed_total: int


class CreateChallengeTypeRequest(BaseModel):
    name: str
    description: Optional[str]
    account_size: float
    price: float
    profit_target_p1: float = 8.0
    profit_target_p2: float = 5.0
    max_daily_loss: float = 5.0
    max_total_loss: float = 10.0
    min_trading_days: int = 5
    max_trading_days: Optional[int] = None
    drawdown_type: str = "trailing"
    consistency_rule: bool = False
    news_trading_ban: bool = False
    is_one_phase: bool = False
    is_instant: bool = False
    is_refundable: bool = False
    max_leverage: int = 50
    profit_split_pct: float = 80.0
    rank_icon: Optional[str] = None
    gradient_bg: Optional[str] = None


# ─── Пользователи ─────────────────────────────────────────────────────────────

@router.get("/users", response_model=APIResponse[list[UserAdminOut]])
async def list_users(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_blocked: Optional[bool] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[UserAdminOut]]:
    """Список пользователей с фильтрами."""
    stmt = select(User)
    if search:
        stmt = stmt.where(
            User.username.ilike(f"%{search}%") | User.first_name.ilike(f"%{search}%")
        )
    if role:
        stmt = stmt.where(User.role == role)
    if is_blocked is not None:
        stmt = stmt.where(User.is_blocked == is_blocked)
    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    users = result.scalars().all()

    # Подсчёт активных испытаний
    result_list = []
    for u in users:
        active_count_result = await session.execute(
            select(func.count(UserChallenge.id)).where(
                UserChallenge.user_id == u.id,
                UserChallenge.status.in_([ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded]),
            )
        )
        active_count = active_count_result.scalar() or 0
        result_list.append(UserAdminOut(
            id=u.id, telegram_id=u.telegram_id, username=u.username,
            first_name=u.first_name, role=u.role, referral_code=u.referral_code,
            streak_days=u.streak_days, is_blocked=u.is_blocked,
            created_at=u.created_at, active_challenges=active_count,
        ))
    return APIResponse(data=result_list)


@router.post("/user/{user_id}/block", response_model=APIResponse[dict])
async def block_user(
    user_id: int,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Блокировка пользователя."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Cannot block super_admin")
    user.is_blocked = not user.is_blocked
    await session.commit()
    return APIResponse(data={"user_id": user_id, "is_blocked": user.is_blocked})


# ─── Испытания ────────────────────────────────────────────────────────────────

@router.get("/challenges/active", response_model=APIResponse[list[ChallengeAdminOut]])
async def list_active_challenges(
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[ChallengeAdminOut]]:
    """Все активные испытания."""
    stmt = (
        select(UserChallenge, User, ChallengeType)
        .join(User, UserChallenge.user_id == User.id)
        .join(ChallengeType, UserChallenge.challenge_type_id == ChallengeType.id)
    )
    if status:
        stmt = stmt.where(UserChallenge.status == status)
    else:
        stmt = stmt.where(UserChallenge.status.in_([
            ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded
        ]))
    stmt = stmt.order_by(UserChallenge.created_at.desc()).limit(limit)
    result = await session.execute(stmt)

    return APIResponse(data=[
        ChallengeAdminOut(
            id=ch.id, user_id=ch.user_id, username=u.username,
            challenge_type_name=ct.name, account_size=float(ct.account_size),
            status=ch.status, phase=ch.phase, account_mode=ch.account_mode,
            total_pnl=float(ch.total_pnl), daily_pnl=float(ch.daily_pnl),
            trading_days_count=ch.trading_days_count, started_at=ch.started_at,
            failed_reason=ch.failed_reason,
        )
        for ch, u, ct in result.all()
    ])


@router.post("/challenges/create", response_model=APIResponse[dict])
async def create_challenge_type(
    body: CreateChallengeTypeRequest,
    admin: User = Depends(require_super_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Создание нового типа испытания."""
    ct = ChallengeType(
        name=body.name,
        description=body.description,
        account_size=Decimal(str(body.account_size)),
        price=Decimal(str(body.price)),
        profit_target_p1=Decimal(str(body.profit_target_p1)),
        profit_target_p2=Decimal(str(body.profit_target_p2)),
        max_daily_loss=Decimal(str(body.max_daily_loss)),
        max_total_loss=Decimal(str(body.max_total_loss)),
        min_trading_days=body.min_trading_days,
        max_trading_days=body.max_trading_days,
        drawdown_type=body.drawdown_type,
        consistency_rule=body.consistency_rule,
        news_trading_ban=body.news_trading_ban,
        is_one_phase=body.is_one_phase,
        is_instant=body.is_instant,
        is_refundable=body.is_refundable,
        max_leverage=body.max_leverage,
        profit_split_pct=Decimal(str(body.profit_split_pct)),
        rank_icon=body.rank_icon,
        gradient_bg=body.gradient_bg,
        is_active=True,
    )
    session.add(ct)
    await session.commit()
    return APIResponse(data={"id": ct.id, "name": ct.name})


# ─── Выплаты ──────────────────────────────────────────────────────────────────

@router.get("/payouts/pending", response_model=APIResponse[list[PayoutAdminOut]])
async def get_pending_payouts(
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[PayoutAdminOut]]:
    """Очередь выплат на рассмотрении."""
    result = await session.execute(
        select(Payout, User)
        .join(User, Payout.user_id == User.id)
        .where(Payout.status == PayoutStatus.pending)
        .order_by(Payout.requested_at)
    )
    return APIResponse(data=[
        PayoutAdminOut(
            id=p.id, user_id=p.user_id, username=u.username,
            challenge_id=p.challenge_id, amount=float(p.amount),
            net_amount=float(p.net_amount), wallet_address=p.wallet_address,
            network=p.network, status=p.status, requested_at=p.requested_at,
            processed_at=p.processed_at, reject_reason=p.reject_reason,
        )
        for p, u in result.all()
    ])


@router.post("/payouts/{payout_id}/approve", response_model=APIResponse[dict])
async def approve_payout(
    payout_id: int,
    tx_hash: Optional[str] = None,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Подтверждение выплаты."""
    result = await session.execute(
        select(Payout).where(Payout.id == payout_id, Payout.status == PayoutStatus.pending)
    )
    payout = result.scalar_one_or_none()
    if not payout:
        raise HTTPException(status_code=404, detail="Pending payout not found")

    payout.status = PayoutStatus.approved
    payout.processed_at = datetime.now()
    if tx_hash:
        payout.tx_hash = tx_hash
        payout.status = PayoutStatus.sent

    await session.commit()

    # Уведомление
    challenge_result = await session.execute(
        select(UserChallenge)
        .where(UserChallenge.id == payout.challenge_id)
        .options(selectinload(UserChallenge.user))
    )
    challenge = challenge_result.scalar_one_or_none()
    if challenge:
        from app.services.notification_service import NotificationService
        notif = NotificationService(session)
        await notif.send_payout_approved(challenge, payout.net_amount)

    return APIResponse(data={"payout_id": payout_id, "status": payout.status})


@router.post("/payouts/{payout_id}/reject", response_model=APIResponse[dict])
async def reject_payout(
    payout_id: int,
    reason: Optional[str] = None,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Отклонение выплаты."""
    result = await session.execute(
        select(Payout).where(Payout.id == payout_id, Payout.status == PayoutStatus.pending)
    )
    payout = result.scalar_one_or_none()
    if not payout:
        raise HTTPException(status_code=404, detail="Pending payout not found")

    payout.status = PayoutStatus.rejected
    payout.processed_at = datetime.now()
    payout.reject_reason = reason
    await session.commit()

    return APIResponse(data={"payout_id": payout_id, "status": "rejected"})


# ─── Обзорная статистика ──────────────────────────────────────────────────────

@router.get("/stats/overview", response_model=APIResponse[OverviewOut])
async def get_overview(
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[OverviewOut]:
    """Общая статистика платформы."""
    # Пользователи
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

    # Активные
    active_challengers = (await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.status.in_([ChallengeStatus.phase1, ChallengeStatus.phase2])
        )
    )).scalar() or 0

    active_funded = (await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.status == ChallengeStatus.funded
        )
    )).scalar() or 0

    # Выплаты
    pending_payouts = (await session.execute(
        select(func.count(Payout.id)).where(Payout.status == PayoutStatus.pending)
    )).scalar() or 0

    pending_amount = (await session.execute(
        select(func.sum(Payout.net_amount)).where(Payout.status == PayoutStatus.pending)
    )).scalar() or 0

    # Выручка (сумма всех покупок испытаний через price * count)
    revenue_result = (await session.execute(
        select(func.sum(ChallengeType.price))
        .join(UserChallenge, ChallengeType.id == UserChallenge.challenge_type_id)
    )).scalar() or 0

    # Пройдено / провалено
    passed = (await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.status == ChallengeStatus.funded
        )
    )).scalar() or 0

    failed = (await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.status == ChallengeStatus.failed
        )
    )).scalar() or 0

    return APIResponse(data=OverviewOut(
        total_users=total_users,
        active_challengers=active_challengers,
        active_funded=active_funded,
        pending_payouts=pending_payouts,
        pending_payout_amount=float(pending_amount),
        total_revenue=float(revenue_result),
        challenges_passed_total=passed,
        challenges_failed_total=failed,
    ))
