"""
/challenges — список испытаний, покупка, детали, правила, нарушения.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from loguru import logger

from app.api.dependencies import get_current_user, rate_limit_standard
from app.core.config import settings
from app.core.database import get_db
from app.core.security import encrypt_aes256, decrypt_aes256
from app.models.challenge import ChallengeStatus, ChallengeType, UserChallenge
from app.models.user import User, UserRole
from app.models.violation import Violation
from app.schemas.common import APIResponse, PaginatedResponse

router = APIRouter(prefix="/challenges", tags=["challenges"])


# ─── Схемы ────────────────────────────────────────────────────────────────────

class ChallengeTypeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    rank_icon: Optional[str]
    gradient_bg: Optional[str]
    account_size: float
    price: float
    profit_target_p1: float
    profit_target_p2: float
    max_daily_loss: float
    max_total_loss: float
    min_trading_days: int
    max_trading_days: Optional[int]
    drawdown_type: str
    consistency_rule: bool
    is_one_phase: bool
    is_instant: bool
    is_refundable: bool
    max_leverage: int
    profit_split_pct: float

    model_config = {"from_attributes": True}


class UserChallengeOut(BaseModel):
    id: int
    challenge_type_id: int
    status: str
    phase: Optional[int]
    account_mode: str
    initial_balance: float
    current_balance: float
    daily_pnl: float
    total_pnl: float
    trading_days_count: int
    started_at: Optional[datetime]
    funded_at: Optional[datetime]
    failed_at: Optional[datetime]
    failed_reason: Optional[str]

    model_config = {"from_attributes": True}


class PurchaseChallengeRequest(BaseModel):
    challenge_type_id: int


class ChallengeRulesOut(BaseModel):
    challenge_id: int
    status: str
    phase: Optional[int]
    # Правила
    profit_target_pct: float
    profit_target_amount: float
    max_daily_loss_pct: float
    max_total_loss_pct: float
    min_trading_days: int
    drawdown_type: str
    consistency_rule: bool
    # Текущее состояние
    current_pnl: float
    current_pnl_pct: float
    daily_pnl: float
    daily_pnl_pct: float
    trading_days_count: int
    # Расчёт сколько можно потерять сегодня
    max_loss_today: float
    # Прогресс правил
    profit_progress_pct: float
    daily_drawdown_used_pct: float
    total_drawdown_used_pct: float


class ViolationOut(BaseModel):
    id: int
    type: str
    description: str
    value: float
    limit_value: float
    occurred_at: datetime

    model_config = {"from_attributes": True}


# ─── Эндпоинты ────────────────────────────────────────────────────────────────

@router.get("", response_model=APIResponse[list[ChallengeTypeOut]])
async def list_challenges(
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_standard),
    __: User = Depends(get_current_user),
) -> APIResponse[list[ChallengeTypeOut]]:
    """Список доступных типов испытаний."""
    stmt = select(ChallengeType).where(ChallengeType.is_active == True).order_by(ChallengeType.account_size)
    result = await session.execute(stmt)
    types = result.scalars().all()
    return APIResponse(data=[ChallengeTypeOut.model_validate(ct) for ct in types])


@router.post("/purchase", response_model=APIResponse[UserChallengeOut])
async def purchase_challenge(
    body: PurchaseChallengeRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_standard),
) -> APIResponse[UserChallengeOut]:
    """
    Покупка испытания — создаёт запись со статусом pending_payment.
    Активация происходит только после подтверждения оплаты администратором.
    """
    # Получаем тип испытания
    ct_result = await session.execute(
        select(ChallengeType).where(
            ChallengeType.id == body.challenge_type_id,
            ChallengeType.is_active == True,
        )
    )
    ct = ct_result.scalar_one_or_none()
    if not ct:
        raise HTTPException(status_code=404, detail="Challenge type not found")

    # Один пользователь — одно активное испытание в любой момент времени.
    existing = await session.execute(
        select(UserChallenge).where(
            UserChallenge.user_id == user.id,
            UserChallenge.status.in_([
                ChallengeStatus.pending_payment,
                ChallengeStatus.phase1,
                ChallengeStatus.phase2,
                ChallengeStatus.funded,
            ]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="You already have an active or pending challenge. Complete or fail the current one before starting a new one.",
        )

    now = datetime.now(timezone.utc)

    # Создаём запись в статусе pending_payment — Bybit аккаунт создадим после подтверждения
    challenge = UserChallenge(
        user_id=user.id,
        challenge_type_id=ct.id,
        status=ChallengeStatus.pending_payment,
        phase=None,
        account_mode="demo",
        exchange="bybit",
        demo_account_id=f"PENDING_{user.telegram_id}_{int(now.timestamp())}",
        demo_api_key_enc="",
        demo_api_secret_enc="",
        initial_balance=ct.account_size,
        current_balance=ct.account_size,
        peak_equity=ct.account_size,
        daily_start_balance=ct.account_size,
        daily_pnl=Decimal("0"),
        total_pnl=Decimal("0"),
        trading_days_count=0,
        started_at=None,
        daily_reset_at=now,
    )
    session.add(challenge)
    await session.flush()

    await session.commit()

    # Уведомляем всех администраторов
    from app.services.notification_service import NotificationService
    notif = NotificationService(session)
    username_str = f"@{user.username}" if user.username else f"tg:{user.telegram_id}"
    await notif.send_payment_pending_to_admins(
        challenge=challenge,
        user_display=username_str,
        plan_name=ct.name,
        plan_price=float(ct.price),
    )

    return APIResponse(data=UserChallengeOut.model_validate(challenge))


@router.get("/my", response_model=APIResponse[list[UserChallengeOut]])
async def my_challenges(
    status_filter: Optional[str] = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[UserChallengeOut]]:
    """Список испытаний текущего пользователя."""
    stmt = select(UserChallenge).where(UserChallenge.user_id == user.id)
    if status_filter:
        stmt = stmt.where(UserChallenge.status == status_filter)
    stmt = stmt.order_by(UserChallenge.created_at.desc())
    result = await session.execute(stmt)
    challenges = result.scalars().all()
    return APIResponse(data=[UserChallengeOut.model_validate(c) for c in challenges])


@router.get("/{challenge_id}", response_model=APIResponse[UserChallengeOut])
async def get_challenge(
    challenge_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[UserChallengeOut]:
    """Детали конкретного испытания."""
    challenge = await _get_user_challenge(challenge_id, user.id, session)
    return APIResponse(data=UserChallengeOut.model_validate(challenge))


@router.get("/{challenge_id}/rules", response_model=APIResponse[ChallengeRulesOut])
async def get_challenge_rules(
    challenge_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[ChallengeRulesOut]:
    """Правила испытания с текущим прогрессом."""
    challenge = await _get_user_challenge(
        challenge_id, user.id, session,
        options=[selectinload(UserChallenge.challenge_type)]
    )
    ct = challenge.challenge_type

    profit_target_pct = (
        ct.profit_target_p1
        if challenge.status == ChallengeStatus.phase1
        else ct.profit_target_p2
    )
    profit_target_amount = float(challenge.initial_balance) * float(profit_target_pct) / 100

    total_pnl = float(challenge.total_pnl)
    total_pnl_pct = (total_pnl / float(challenge.initial_balance)) * 100
    daily_pnl = float(challenge.daily_pnl)
    daily_pnl_pct = (daily_pnl / float(challenge.daily_start_balance)) * 100 if challenge.daily_start_balance else 0

    # Сколько можно потерять сегодня
    max_loss_today = float(challenge.daily_start_balance) * float(ct.max_daily_loss) / 100
    max_loss_today_left = max_loss_today + daily_pnl  # если daily_pnl отрицательный

    daily_dd_used = max(0, -daily_pnl / float(challenge.daily_start_balance) * 100) if challenge.daily_start_balance else 0
    total_dd_used = max(0, -total_pnl / float(challenge.initial_balance) * 100) if challenge.initial_balance else 0

    rules = ChallengeRulesOut(
        challenge_id=challenge.id,
        status=challenge.status,
        phase=challenge.phase,
        profit_target_pct=float(profit_target_pct),
        profit_target_amount=profit_target_amount,
        max_daily_loss_pct=float(ct.max_daily_loss),
        max_total_loss_pct=float(ct.max_total_loss),
        min_trading_days=ct.min_trading_days,
        drawdown_type=ct.drawdown_type,
        consistency_rule=ct.consistency_rule,
        current_pnl=total_pnl,
        current_pnl_pct=total_pnl_pct,
        daily_pnl=daily_pnl,
        daily_pnl_pct=daily_pnl_pct,
        trading_days_count=challenge.trading_days_count,
        max_loss_today=max_loss_today_left,
        profit_progress_pct=min(100, (total_pnl_pct / float(profit_target_pct)) * 100),
        daily_drawdown_used_pct=min(100, (daily_dd_used / float(ct.max_daily_loss)) * 100),
        total_drawdown_used_pct=min(100, (total_dd_used / float(ct.max_total_loss)) * 100),
    )
    return APIResponse(data=rules)


@router.get("/{challenge_id}/violations", response_model=APIResponse[list[ViolationOut]])
async def get_challenge_violations(
    challenge_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[ViolationOut]]:
    """История нарушений для испытания."""
    await _get_user_challenge(challenge_id, user.id, session)
    result = await session.execute(
        select(Violation)
        .where(Violation.challenge_id == challenge_id)
        .order_by(Violation.occurred_at.desc())
    )
    violations = result.scalars().all()
    return APIResponse(data=[ViolationOut.model_validate(v) for v in violations])


@router.get("/{challenge_id}/account-details", response_model=APIResponse[dict])
async def get_account_details(
    challenge_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Возвращает детали Bybit суб-аккаунта (имя пользователя, UID, API ключ)."""
    challenge = await _get_user_challenge(challenge_id, user.id, session)
    if challenge.status not in (
        ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded
    ):
        raise HTTPException(status_code=403, detail="Account details available only for active challenges")

    api_key = ""
    if challenge.demo_api_key_enc:
        try:
            api_key = decrypt_aes256(challenge.demo_api_key_enc)
        except Exception:
            pass

    return APIResponse(data={
        "bybit_uid": challenge.demo_account_id,
        "username": challenge.demo_account_username or "",
        "api_key": api_key,
        "account_mode": challenge.account_mode,
    })


# ─── Вспомогательные функции ──────────────────────────────────────────────────

async def _get_user_challenge(
    challenge_id: int,
    user_id: int,
    session: AsyncSession,
    options: list = None,
) -> UserChallenge:
    stmt = select(UserChallenge).where(
        UserChallenge.id == challenge_id,
        UserChallenge.user_id == user_id,
    )
    if options:
        for opt in options:
            stmt = stmt.options(opt)
    result = await session.execute(stmt)
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    return challenge
