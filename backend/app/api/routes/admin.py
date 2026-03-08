"""
/admin — административные эндпоинты (только admin/super_admin).
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from datetime import timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user, require_admin, require_super_admin
from app.core.database import get_db
from app.models.challenge import AccountMode, ChallengeStatus, ChallengeType, UserChallenge
from app.models.payout import Payout, PayoutStatus
from app.models.user import User, UserRole
from app.schemas.common import APIResponse, PaginatedResponse

router = APIRouter(prefix="/admin", tags=["admin"])

# Telegram IDs с правом bootstrap (без авторизации)
BOOTSTRAP_TELEGRAM_IDS: set[int] = {705020259, 445677777}


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


# ─── Ручная активация испытания ───────────────────────────────────────────────

class ManualActivateRequest(BaseModel):
    user_telegram_id: int
    account_size: float


@router.post("/challenges/activate-manual", response_model=APIResponse[dict])
async def activate_challenge_manual(
    body: ManualActivateRequest,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """
    Ручная активация испытания для пользователя после подтверждения оплаты.
    Создаёт испытание без обращения к Bybit API.
    """
    from datetime import datetime, timezone

    user_result = await session.execute(
        select(User).where(User.telegram_id == body.user_telegram_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail=f"User with telegram_id {body.user_telegram_id} not found")

    ct_result = await session.execute(
        select(ChallengeType).where(
            ChallengeType.account_size == body.account_size,
            ChallengeType.is_active == True,
        ).limit(1)
    )
    ct = ct_result.scalar_one_or_none()
    if not ct:
        raise HTTPException(status_code=404, detail=f"No active challenge type found for size ${body.account_size}")

    now = datetime.now(timezone.utc)
    challenge = UserChallenge(
        user_id=user.id,
        challenge_type_id=ct.id,
        status=ChallengeStatus.phase1,
        phase=1,
        account_mode="demo",
        exchange="bybit",
        demo_account_id=f"MANUAL_{user.telegram_id}_{int(now.timestamp())}",
        demo_api_key_enc="",
        demo_api_secret_enc="",
        initial_balance=Decimal(str(body.account_size)),
        current_balance=Decimal(str(body.account_size)),
        peak_equity=Decimal(str(body.account_size)),
        daily_start_balance=Decimal(str(body.account_size)),
        daily_pnl=Decimal("0"),
        total_pnl=Decimal("0"),
        trading_days_count=0,
        started_at=now,
        daily_reset_at=now,
    )
    session.add(challenge)

    if user.role == UserRole.guest:
        user.role = UserRole.challenger

    await session.commit()
    return APIResponse(data={
        "challenge_id": challenge.id,
        "user_id": user.id,
        "account_size": body.account_size,
        "status": "phase1",
        "note": "Created manually without Bybit API",
    })


# ─── Дополнительные эндпоинты для фронтенд-панели ─────────────────────────────

class OverviewExtOut(BaseModel):
    total_users: int
    active_users_today: int
    total_challenges: int
    active_challenges: int
    funded_accounts: int
    total_pnl_all: float
    pending_payouts: int
    pending_payout_amount: float
    master_balance: float


@router.get("/overview", response_model=APIResponse[OverviewExtOut])
async def get_overview_ext(
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[OverviewExtOut]:
    """Расширенная статистика для фронтенд-панели."""
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

    # Active today (updated_at within last 24h)
    active_today = (await session.execute(
        select(func.count(User.id)).where(User.updated_at >= today_start)
    )).scalar() or 0

    total_challenges = (await session.execute(select(func.count(UserChallenge.id)))).scalar() or 0

    active_chal = (await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.status.in_([ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded])
        )
    )).scalar() or 0

    funded = (await session.execute(
        select(func.count(UserChallenge.id)).where(UserChallenge.status == ChallengeStatus.funded)
    )).scalar() or 0

    total_pnl = (await session.execute(
        select(func.sum(UserChallenge.total_pnl))
    )).scalar() or 0

    pending_count = (await session.execute(
        select(func.count(Payout.id)).where(Payout.status == PayoutStatus.pending)
    )).scalar() or 0

    pending_amt = (await session.execute(
        select(func.sum(Payout.amount)).where(Payout.status == PayoutStatus.pending)
    )).scalar() or 0

    return APIResponse(data=OverviewExtOut(
        total_users=total_users,
        active_users_today=active_today,
        total_challenges=total_challenges,
        active_challenges=active_chal,
        funded_accounts=funded,
        total_pnl_all=float(total_pnl),
        pending_payouts=pending_count,
        pending_payout_amount=float(pending_amt),
        master_balance=0.0,  # fetched separately in master balance check task
    ))


class UsersPageOut(BaseModel):
    users: list[UserAdminOut]
    total: int


@router.get("/users", response_model=APIResponse[UsersPageOut])
async def list_users_paged(
    search: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_blocked: Optional[bool] = Query(None),
    limit: int = Query(20, le=200),
    offset: int = Query(0),
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[UsersPageOut]:
    """Список пользователей с постраничной навигацией."""
    stmt = select(User)
    if search:
        stmt = stmt.where(
            User.username.ilike(f"%{search}%") | User.first_name.ilike(f"%{search}%")
        )
    if role:
        stmt = stmt.where(User.role == role)
    if is_blocked is not None:
        stmt = stmt.where(User.is_blocked == is_blocked)

    count_q = await session.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_q.scalar_one() or 0

    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    users = result.scalars().all()

    result_list = []
    for u in users:
        ac = (await session.execute(
            select(func.count(UserChallenge.id)).where(
                UserChallenge.user_id == u.id,
                UserChallenge.status.in_([ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded]),
            )
        )).scalar() or 0
        result_list.append(UserAdminOut(
            id=u.id, telegram_id=u.telegram_id, username=u.username,
            first_name=u.first_name, role=u.role, referral_code=u.referral_code,
            streak_days=u.streak_days, is_blocked=u.is_blocked,
            created_at=u.created_at, active_challenges=ac,
        ))

    return APIResponse(data=UsersPageOut(users=result_list, total=total))


@router.post("/users/{user_id}/block", response_model=APIResponse[dict])
async def block_user_by_id(
    user_id: int,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.super_admin:
        raise HTTPException(status_code=403, detail="Cannot block super_admin")
    user.is_blocked = True
    await session.commit()
    return APIResponse(data={"user_id": user_id, "is_blocked": True})


@router.post("/users/{user_id}/unblock", response_model=APIResponse[dict])
async def unblock_user_by_id(
    user_id: int,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_blocked = False
    await session.commit()
    return APIResponse(data={"user_id": user_id, "is_blocked": False})


class ChallengesPageOut(BaseModel):
    challenges: list[ChallengeAdminOut]
    total: int


@router.get("/challenges", response_model=APIResponse[ChallengesPageOut])
async def list_challenges_paged(
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=200),
    offset: int = Query(0),
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[ChallengesPageOut]:
    """Испытания с постраничной навигацией."""
    stmt = (
        select(UserChallenge, User, ChallengeType)
        .join(User, UserChallenge.user_id == User.id)
        .join(ChallengeType, UserChallenge.challenge_type_id == ChallengeType.id)
    )
    if status:
        stmt = stmt.where(UserChallenge.status == status)

    count_q = await session.execute(select(func.count()).select_from(stmt.subquery()))
    total = count_q.scalar_one() or 0

    stmt = stmt.order_by(UserChallenge.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)

    challenges = [
        ChallengeAdminOut(
            id=ch.id, user_id=ch.user_id, username=u.username,
            challenge_type_name=ct.name, account_size=float(ct.account_size),
            status=ch.status, phase=ch.phase, account_mode=ch.account_mode,
            total_pnl=float(ch.total_pnl), daily_pnl=float(ch.daily_pnl),
            trading_days_count=ch.trading_days_count, started_at=ch.started_at,
            failed_reason=ch.failed_reason,
        )
        for ch, u, ct in result.all()
    ]
    return APIResponse(data=ChallengesPageOut(challenges=challenges, total=total))


@router.get("/payouts", response_model=APIResponse[list[PayoutAdminOut]])
async def list_payouts(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[PayoutAdminOut]]:
    """Выплаты с фильтром по статусу."""
    stmt = (
        select(Payout, User)
        .join(User, Payout.user_id == User.id)
        .order_by(Payout.requested_at.desc())
        .limit(limit)
    )
    if status:
        stmt = stmt.where(Payout.status == status)

    result = await session.execute(stmt)
    return APIResponse(data=[
        PayoutAdminOut(
            id=p.id, user_id=p.user_id, username=u.username,
            challenge_id=p.challenge_id, amount=float(p.amount),
            net_amount=float(p.net_amount or p.amount), wallet_address=p.wallet_address,
            network=p.network, status=p.status, requested_at=p.requested_at,
            processed_at=p.processed_at, reject_reason=getattr(p, 'reject_reason', None),
        )
        for p, u in result.all()
    ])


# ═══════════════════════════════════════════════════════════════════════════════
# ─── DEVTOOLS — тестирование и отладка ────────────────────────────────────────
# ═══════════════════════════════════════════════════════════════════════════════

class SetRoleRequest(BaseModel):
    role: str


class GrantChallengeRequest(BaseModel):
    user_id: int
    challenge_type_id: int


class ForceStatusRequest(BaseModel):
    status: str
    reset_pnl: bool = False


class AddPnlRequest(BaseModel):
    amount: float
    add_day: bool = True


# ─── Активация pending испытания через Bybit ──────────────────────────────────

@router.post("/challenges/{challenge_id}/activate-bybit", response_model=APIResponse[dict])
async def activate_challenge_bybit(
    challenge_id: int,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """
    Создать Bybit Testnet суб-аккаунт для pending_payment испытания и активировать его.
    Используется когда автоматическое создание не сработало.
    Testnet (api-testnet.bybit.com) поддерживает создание суб-аккаунтов.
    """
    from datetime import datetime, timezone
    from app.core.security import encrypt_aes256
    from app.services.exchange.bybit_master import BybitMasterClient

    ch = await session.get(UserChallenge, challenge_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Испытание не найдено")

    user_result = await session.execute(select(User).where(User.id == ch.user_id))
    user = user_result.scalar_one_or_none()

    master = BybitMasterClient(mode="testnet")
    try:
        testnet_account = await master.setup_testnet_challenge_account(
            account_size=ch.initial_balance,
            username_prefix=f"CHM{user.telegram_id if user else ch.user_id}",
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Bybit Testnet API error: {str(e)}")
    finally:
        await master.close()

    now = datetime.now(timezone.utc)
    ch.demo_account_id = testnet_account["account_id"]
    ch.demo_account_username = testnet_account.get("username", "")
    ch.demo_api_key_enc = encrypt_aes256(testnet_account["api_key"])
    ch.demo_api_secret_enc = encrypt_aes256(testnet_account["api_secret"])
    ch.status = ChallengeStatus.phase1
    ch.started_at = now
    ch.daily_reset_at = now

    if user and user.role == UserRole.guest:
        user.role = UserRole.challenger

    await session.commit()
    return APIResponse(data={
        "challenge_id": challenge_id,
        "bybit_uid": testnet_account["account_id"],
        "bybit_username": testnet_account.get("username", ""),
        "exchange": "bybit_testnet",
        "status": "phase1",
    })


# ─── Удаление испытания (super_admin) ─────────────────────────────────────────

@router.delete("/challenges/{challenge_id}", response_model=APIResponse[dict])
async def delete_challenge(
    challenge_id: int,
    admin: User = Depends(require_super_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """
    Полное удаление испытания (super_admin only).
    Каскадно удаляет связанные trade/violation/payout записи.
    """
    from app.models.trade import Trade
    from app.models.violation import Violation
    from sqlalchemy import delete as sa_delete

    ch = await session.get(UserChallenge, challenge_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Испытание не найдено")

    # Каскадно удаляем зависимые записи
    await session.execute(sa_delete(Trade).where(Trade.challenge_id == challenge_id))
    await session.execute(sa_delete(Violation).where(Violation.challenge_id == challenge_id))

    # Удаляем связанные выплаты (только pending — approved нельзя отменить)
    await session.execute(
        sa_delete(Payout).where(
            Payout.challenge_id == challenge_id,
            Payout.status.in_(["pending", "rejected"]),
        )
    )

    await session.delete(ch)
    await session.commit()
    return APIResponse(data={"challenge_id": challenge_id, "deleted": True})


# ─── Bootstrap (без авторизации) ─────────────────────────────────────────────

@router.post("/bootstrap", response_model=APIResponse[dict])
async def bootstrap_admin(
    telegram_id: int = Body(..., embed=True),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Выдать super_admin разрешённому Telegram ID (без авторизации)."""
    BOOTSTRAP_IDS: set[int] = {705020259, 445677777}
    if telegram_id not in BOOTSTRAP_IDS:
        raise HTTPException(status_code=403, detail="Telegram ID не в списке разрешённых")
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404,
            detail="Пользователь не найден. Сначала открой бота (/start)")
    user.role = UserRole.super_admin
    await session.commit()
    return APIResponse(data={"telegram_id": telegram_id, "role": "super_admin", "ok": True})


# ─── Найти пользователя по Telegram ID ────────────────────────────────────────

@router.get("/users/by-tgid/{telegram_id}", response_model=APIResponse[UserAdminOut])
async def get_user_by_telegram_id(
    telegram_id: int,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[UserAdminOut]:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    ac = (await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.user_id == user.id,
            UserChallenge.status.in_([ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded]),
        )
    )).scalar() or 0
    return APIResponse(data=UserAdminOut(
        id=user.id, telegram_id=user.telegram_id, username=user.username,
        first_name=user.first_name, role=user.role, referral_code=user.referral_code,
        streak_days=user.streak_days, is_blocked=user.is_blocked,
        created_at=user.created_at, active_challenges=ac,
    ))


# ─── Установить роль пользователя ─────────────────────────────────────────────

@router.post("/users/{user_id}/set-role", response_model=APIResponse[dict])
async def set_user_role(
    user_id: int,
    body: SetRoleRequest,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    allowed = {r.value for r in UserRole}
    if body.role not in allowed:
        raise HTTPException(status_code=400, detail=f"Роль должна быть одной из: {allowed}")
    user.role = body.role
    await session.commit()
    return APIResponse(data={"user_id": user_id, "role": body.role})


# ─── Получить испытания пользователя (admin view) ─────────────────────────────

@router.get("/users/{user_id}/challenges", response_model=APIResponse[list[ChallengeAdminOut]])
async def get_user_challenges_admin(
    user_id: int,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[ChallengeAdminOut]]:
    result = await session.execute(
        select(UserChallenge, ChallengeType)
        .join(ChallengeType, UserChallenge.challenge_type_id == ChallengeType.id)
        .where(UserChallenge.user_id == user_id)
        .order_by(UserChallenge.created_at.desc())
        .limit(20)
    )
    user = await session.get(User, user_id)
    uname = user.username if user else None
    return APIResponse(data=[
        ChallengeAdminOut(
            id=ch.id, user_id=ch.user_id, username=uname,
            challenge_type_name=ct.name, account_size=float(ct.account_size),
            status=ch.status, phase=ch.phase, account_mode=ch.account_mode,
            total_pnl=float(ch.total_pnl), daily_pnl=float(ch.daily_pnl),
            trading_days_count=ch.trading_days_count, started_at=ch.started_at,
            failed_reason=ch.failed_reason,
        )
        for ch, ct in result.all()
    ])


# ─── Выдать испытание пользователю (bypass payment) ───────────────────────────

@router.post("/challenges/grant", response_model=APIResponse[dict])
async def grant_challenge_to_user(
    body: GrantChallengeRequest,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    from datetime import timezone as tz
    ct = await session.get(ChallengeType, body.challenge_type_id)
    if not ct:
        raise HTTPException(status_code=404, detail="Тип испытания не найден")
    user = await session.get(User, body.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    now = datetime.now(tz.utc)
    ch = UserChallenge(
        user_id=body.user_id,
        challenge_type_id=body.challenge_type_id,
        status=ChallengeStatus.phase1,
        phase=1,
        account_mode=AccountMode.demo,
        initial_balance=ct.account_size,
        current_balance=ct.account_size,
        peak_equity=ct.account_size,
        daily_start_balance=ct.account_size,
        total_pnl=Decimal("0"),
        daily_pnl=Decimal("0"),
        trading_days_count=0,
        started_at=now,
        daily_reset_at=now,
    )
    session.add(ch)
    if user.role not in (UserRole.admin, UserRole.super_admin):
        user.role = UserRole.challenger
    await session.commit()
    await session.refresh(ch)
    return APIResponse(data={"challenge_id": ch.id, "status": ch.status,
                             "account_size": float(ct.account_size)})


# ─── Принудительно изменить статус испытания ──────────────────────────────────

@router.post("/challenges/{challenge_id}/force-status", response_model=APIResponse[dict])
async def force_challenge_status(
    challenge_id: int,
    body: ForceStatusRequest,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    from datetime import timezone as tz
    ch = await session.get(UserChallenge, challenge_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Испытание не найдено")
    now = datetime.now(tz.utc)
    if body.status == "phase1":
        ch.status = ChallengeStatus.phase1
        ch.phase = 1
        ch.account_mode = AccountMode.demo
        ch.failed_at = None
        ch.failed_reason = None
    elif body.status == "phase2":
        ch.status = ChallengeStatus.phase2
        ch.phase = 2
        ch.account_mode = AccountMode.demo
    elif body.status == "funded":
        ch.status = ChallengeStatus.funded
        ch.phase = None
        ch.account_mode = AccountMode.funded
        ch.funded_at = now
        user = await session.get(User, ch.user_id)
        if user and user.role not in (UserRole.admin, UserRole.super_admin):
            user.role = UserRole.funded_trader
    elif body.status == "failed":
        ch.status = ChallengeStatus.failed
        ch.failed_at = now
        ch.failed_reason = "Admin force-failed"
    else:
        raise HTTPException(status_code=400, detail="Статус: phase1, phase2, funded, failed")
    if body.reset_pnl:
        ch.total_pnl = Decimal("0")
        ch.daily_pnl = Decimal("0")
        ch.current_balance = ch.initial_balance
        ch.trading_days_count = 0
    await session.commit()
    return APIResponse(data={"challenge_id": challenge_id, "status": body.status})


# ─── Добавить PnL к испытанию ─────────────────────────────────────────────────

@router.post("/challenges/{challenge_id}/add-pnl", response_model=APIResponse[dict])
async def add_pnl_to_challenge(
    challenge_id: int,
    body: AddPnlRequest,
    admin: User = Depends(require_admin()),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    ch = await session.get(UserChallenge, challenge_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Испытание не найдено")
    amount = Decimal(str(body.amount))
    ch.total_pnl += amount
    ch.daily_pnl += amount
    ch.current_balance += amount
    if ch.current_balance > ch.peak_equity:
        ch.peak_equity = ch.current_balance
    if body.add_day and body.amount != 0:
        ch.trading_days_count += 1
    await session.commit()
    return APIResponse(data={
        "challenge_id": challenge_id,
        "total_pnl": float(ch.total_pnl),
        "current_balance": float(ch.current_balance),
        "trading_days_count": ch.trading_days_count,
    })
