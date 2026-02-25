import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Account, AccountPhase, AccountStatus, Trade, TradeStatus, User
from routers.auth import get_current_user
from services.pnl_calculator import (
    calculate_daily_drawdown_pct,
    calculate_equity,
    calculate_profit_progress_pct,
    calculate_trailing_drawdown_pct,
    calculate_win_rate,
)
from services.price_feed import fetch_all_prices
from services.risk_manager import check_and_update_day_start

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/account", tags=["account"])


class AccountOverviewResponse(BaseModel):
    account_id: int
    phase: str
    status: str
    attempt_number: int
    current_balance: str
    initial_balance: str
    equity: str
    peak_equity: str
    day_start_balance: str
    unrealized_pnl: str
    daily_pnl: str
    daily_drawdown_pct: str
    trailing_drawdown_pct: str
    profit_target_pct: str
    profit_progress_pct: str
    max_daily_drawdown_pct: str
    max_trailing_drawdown_pct: str
    trading_days_count: int
    min_trading_days: int
    total_trades: int
    winning_trades: int
    win_rate: str
    profit_split_pct: str
    fail_reason: Optional[str]
    fail_detail: Optional[str]
    failed_at: Optional[str]
    open_positions_count: int


class TradeHistoryItem(BaseModel):
    id: int
    symbol: str
    direction: str
    leverage: int
    entry_price: str
    close_price: Optional[str]
    take_profit: str
    stop_loss: str
    position_size: str
    notional_value: str
    realized_pnl: Optional[str]
    close_reason: Optional[str]
    opened_at: str
    closed_at: Optional[str]
    status: str


class RestartAccountResponse(BaseModel):
    account_id: int
    phase: str
    status: str
    attempt_number: int
    message: str


@router.get("/overview", response_model=AccountOverviewResponse)
async def get_account_overview(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user, account = await get_current_user(token, db)

    await check_and_update_day_start(account, db)

    result = await db.execute(
        select(Trade).where(
            Trade.account_id == account.id,
            Trade.status == TradeStatus.OPEN,
        )
    )
    open_trades = result.scalars().all()

    prices = await fetch_all_prices()
    equity = calculate_equity(account, open_trades, prices)

    balance = Decimal(str(account.current_balance))
    initial = Decimal(str(account.initial_balance))
    day_start = Decimal(str(account.day_start_balance))
    peak = Decimal(str(account.peak_equity))

    unrealized_pnl = equity - balance
    daily_pnl = equity - day_start
    daily_dd = calculate_daily_drawdown_pct(equity, day_start)
    trailing_dd = calculate_trailing_drawdown_pct(equity, peak)
    progress = calculate_profit_progress_pct(account)
    win_rate = calculate_win_rate(account.total_trades, account.winning_trades)

    await db.commit()

    return AccountOverviewResponse(
        account_id=account.id,
        phase=account.phase.value,
        status=account.status.value,
        attempt_number=account.attempt_number,
        current_balance=str(balance.quantize(Decimal("0.01"))),
        initial_balance=str(initial.quantize(Decimal("0.01"))),
        equity=str(equity.quantize(Decimal("0.01"))),
        peak_equity=str(peak.quantize(Decimal("0.01"))),
        day_start_balance=str(day_start.quantize(Decimal("0.01"))),
        unrealized_pnl=str(unrealized_pnl.quantize(Decimal("0.01"))),
        daily_pnl=str(daily_pnl.quantize(Decimal("0.01"))),
        daily_drawdown_pct=str(daily_dd),
        trailing_drawdown_pct=str(trailing_dd),
        profit_target_pct=str(account.profit_target_pct),
        profit_progress_pct=str(progress),
        max_daily_drawdown_pct=str(account.max_daily_drawdown_pct),
        max_trailing_drawdown_pct=str(account.max_trailing_drawdown_pct),
        trading_days_count=account.trading_days_count,
        min_trading_days=account.min_trading_days,
        total_trades=account.total_trades,
        winning_trades=account.winning_trades,
        win_rate=str(win_rate),
        profit_split_pct=str(account.profit_split_pct),
        fail_reason=account.fail_reason.value if account.fail_reason else None,
        fail_detail=account.fail_detail,
        failed_at=account.failed_at.isoformat() if account.failed_at else None,
        open_positions_count=len(open_trades),
    )


@router.get("/history", response_model=List[TradeHistoryItem])
async def get_trade_history(
    authorization: str = Header(...),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user, account = await get_current_user(token, db)

    if limit > 200:
        limit = 200

    result = await db.execute(
        select(Trade).where(
            Trade.account_id == account.id,
            Trade.status == TradeStatus.CLOSED,
        )
        .order_by(Trade.closed_at.desc())
        .limit(limit)
        .offset(offset)
    )
    trades = result.scalars().all()

    return [
        TradeHistoryItem(
            id=t.id,
            symbol=t.symbol,
            direction=t.direction.value,
            leverage=t.leverage,
            entry_price=str(t.entry_price),
            close_price=str(t.close_price) if t.close_price else None,
            take_profit=str(t.take_profit),
            stop_loss=str(t.stop_loss),
            position_size=str(t.position_size),
            notional_value=str(t.notional_value),
            realized_pnl=str(t.realized_pnl) if t.realized_pnl is not None else None,
            close_reason=t.close_reason.value if t.close_reason else None,
            opened_at=t.opened_at.isoformat(),
            closed_at=t.closed_at.isoformat() if t.closed_at else None,
            status=t.status.value,
        )
        for t in trades
    ]


@router.post("/restart", response_model=RestartAccountResponse)
async def restart_account(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """Начать новую попытку после провала."""
    token = authorization.replace("Bearer ", "")
    user, account = await get_current_user(token, db)

    if account.status != AccountStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail="Аккаунт не в статусе FAILED. Рестарт невозможен.",
        )

    # Закрываем все открытые позиции (если остались)
    result = await db.execute(
        select(Trade).where(
            Trade.account_id == account.id,
            Trade.status == TradeStatus.OPEN,
        )
    )
    open_trades = result.scalars().all()
    now = datetime.now(timezone.utc)
    for t in open_trades:
        t.status = TradeStatus.CLOSED
        t.closed_at = now
        db.add(t)

    # Создаём новый аккаунт (новая попытка)
    new_account = Account(
        user_id=user.id,
        phase=AccountPhase.EVALUATION,
        status=AccountStatus.ACTIVE,
        attempt_number=account.attempt_number + 1,
        day_start_date=now.replace(hour=0, minute=0, second=0, microsecond=0),
    )
    db.add(new_account)
    await db.commit()
    await db.refresh(new_account)

    # Обновляем сессию на новый аккаунт (аккаунт выбирается по последнему created_at)
    return RestartAccountResponse(
        account_id=new_account.id,
        phase=new_account.phase.value,
        status=new_account.status.value,
        attempt_number=new_account.attempt_number,
        message="Новый аккаунт создан. Удачи в торговле!",
    )
