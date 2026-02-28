"""
/stats — дашборд, equity curve, performance метрики.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.challenge import ChallengeStatus, UserChallenge
from app.models.trade import Trade
from app.models.user import User
from app.schemas.common import APIResponse

router = APIRouter(prefix="/stats", tags=["stats"])


class DashboardOut(BaseModel):
    # Активное испытание
    active_challenge_id: Optional[int]
    challenge_status: Optional[str]
    account_mode: Optional[str]
    phase: Optional[int]
    # Баланс
    current_balance: float
    initial_balance: float
    equity: float
    daily_pnl: float
    total_pnl: float
    total_pnl_pct: float
    # Прогресс
    profit_target_pct: float
    profit_progress_pct: float
    # Просадка (% от лимита)
    daily_dd_pct: float
    total_dd_pct: float
    daily_dd_limit: float
    total_dd_limit: float
    # Торговые дни
    trading_days_count: int
    min_trading_days: int
    # Streak
    streak_days: int


class EquityCurvePoint(BaseModel):
    timestamp: int  # unix ms
    equity: float
    pnl: float


class PerformanceOut(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    avg_rr: float
    max_drawdown_pct: float
    best_trade_pnl: float
    worst_trade_pnl: float
    avg_duration_hours: float


@router.get("/dashboard", response_model=APIResponse[DashboardOut])
async def get_dashboard(
    challenge_id: Optional[int] = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[DashboardOut]:
    """Данные для главного дашборда."""
    # Если challenge_id не указан — берём последнее активное
    if challenge_id:
        stmt = select(UserChallenge).where(
            UserChallenge.id == challenge_id,
            UserChallenge.user_id == user.id,
        ).options(selectinload(UserChallenge.challenge_type))
    else:
        stmt = (
            select(UserChallenge)
            .where(
                UserChallenge.user_id == user.id,
                UserChallenge.status.in_([
                    ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded
                ]),
            )
            .options(selectinload(UserChallenge.challenge_type))
            .order_by(UserChallenge.created_at.desc())
        )

    result = await session.execute(stmt)
    challenge = result.scalars().first()

    if not challenge:
        # Нет активных — возвращаем пустой дашборд
        return APIResponse(data=DashboardOut(
            active_challenge_id=None, challenge_status=None, account_mode=None, phase=None,
            current_balance=0, initial_balance=0, equity=0, daily_pnl=0, total_pnl=0,
            total_pnl_pct=0, profit_target_pct=0, profit_progress_pct=0,
            daily_dd_pct=0, total_dd_pct=0, daily_dd_limit=5, total_dd_limit=10,
            trading_days_count=0, min_trading_days=5, streak_days=user.streak_days,
        ))

    ct = challenge.challenge_type
    total_pnl = float(challenge.total_pnl)
    initial = float(challenge.initial_balance)
    total_pnl_pct = (total_pnl / initial * 100) if initial else 0

    profit_target = float(
        ct.profit_target_p1 if challenge.status == ChallengeStatus.phase1
        else ct.profit_target_p2
    )

    daily_pnl = float(challenge.daily_pnl)
    daily_start = float(challenge.daily_start_balance)
    daily_dd_pct = (-daily_pnl / daily_start * 100) if daily_start and daily_pnl < 0 else 0
    total_dd_pct = (-total_pnl / initial * 100) if initial and total_pnl < 0 else 0

    return APIResponse(data=DashboardOut(
        active_challenge_id=challenge.id,
        challenge_status=challenge.status,
        account_mode=challenge.account_mode,
        phase=challenge.phase,
        current_balance=float(challenge.current_balance),
        initial_balance=initial,
        equity=float(challenge.current_balance),
        daily_pnl=daily_pnl,
        total_pnl=total_pnl,
        total_pnl_pct=round(total_pnl_pct, 2),
        profit_target_pct=profit_target,
        profit_progress_pct=round(min(100, (total_pnl_pct / profit_target * 100) if profit_target else 0), 2),
        daily_dd_pct=round(daily_dd_pct, 2),
        total_dd_pct=round(total_dd_pct, 2),
        daily_dd_limit=float(ct.max_daily_loss),
        total_dd_limit=float(ct.max_total_loss),
        trading_days_count=challenge.trading_days_count,
        min_trading_days=ct.min_trading_days,
        streak_days=user.streak_days,
    ))


@router.get("/equity-curve", response_model=APIResponse[list[EquityCurvePoint]])
async def get_equity_curve(
    challenge_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[EquityCurvePoint]]:
    """
    Equity curve для графика — закрытые сделки с кумулятивным PnL.
    """
    # Проверяем принадлежность
    challenge_result = await session.execute(
        select(UserChallenge).where(
            UserChallenge.id == challenge_id,
            UserChallenge.user_id == user.id,
        )
    )
    challenge = challenge_result.scalar_one_or_none()
    if not challenge:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Challenge not found")

    trades_result = await session.execute(
        select(Trade)
        .where(
            Trade.challenge_id == challenge_id,
            Trade.closed_at.isnot(None),
            Trade.pnl.isnot(None),
        )
        .order_by(Trade.closed_at)
    )
    trades = trades_result.scalars().all()

    points = []
    cumulative_pnl = 0.0
    base = float(challenge.initial_balance)

    for trade in trades:
        cumulative_pnl += float(trade.pnl)
        points.append(EquityCurvePoint(
            timestamp=int(trade.closed_at.timestamp() * 1000),
            equity=base + cumulative_pnl,
            pnl=round(cumulative_pnl, 2),
        ))

    return APIResponse(data=points)


@router.get("/performance", response_model=APIResponse[PerformanceOut])
async def get_performance(
    challenge_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[PerformanceOut]:
    """Win rate, avg RR, profit factor и другие метрики."""
    challenge_result = await session.execute(
        select(UserChallenge).where(
            UserChallenge.id == challenge_id,
            UserChallenge.user_id == user.id,
        )
    )
    if not challenge_result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Challenge not found")

    trades_result = await session.execute(
        select(Trade)
        .where(
            Trade.challenge_id == challenge_id,
            Trade.closed_at.isnot(None),
            Trade.pnl.isnot(None),
        )
    )
    trades = trades_result.scalars().all()

    if not trades:
        return APIResponse(data=PerformanceOut(
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0,
            avg_profit=0, avg_loss=0, profit_factor=0, avg_rr=0,
            max_drawdown_pct=0, best_trade_pnl=0, worst_trade_pnl=0, avg_duration_hours=0,
        ))

    pnls = [float(t.pnl) for t in trades]
    profits = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    durations = [t.duration_seconds for t in trades if t.duration_seconds]

    total = len(pnls)
    win_count = len(profits)
    loss_count = len(losses)

    avg_profit = sum(profits) / len(profits) if profits else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0
    profit_factor = (sum(profits) / abs(sum(losses))) if losses and sum(losses) != 0 else float("inf")
    win_rate = (win_count / total * 100) if total else 0
    avg_duration_hours = (sum(durations) / len(durations) / 3600) if durations else 0

    # Max drawdown из equity curve
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnls:
        cumulative += p
        if cumulative > peak:
            peak = cumulative
        dd = (peak - cumulative) / (peak + 1e-9) * 100
        if dd > max_dd:
            max_dd = dd

    return APIResponse(data=PerformanceOut(
        total_trades=total,
        winning_trades=win_count,
        losing_trades=loss_count,
        win_rate=round(win_rate, 1),
        avg_profit=round(avg_profit, 2),
        avg_loss=round(avg_loss, 2),
        profit_factor=round(profit_factor, 2),
        avg_rr=round(avg_profit / avg_loss, 2) if avg_loss else 0,
        max_drawdown_pct=round(max_dd, 2),
        best_trade_pnl=round(max(pnls), 2) if pnls else 0,
        worst_trade_pnl=round(min(pnls), 2) if pnls else 0,
        avg_duration_hours=round(avg_duration_hours, 1),
    ))
