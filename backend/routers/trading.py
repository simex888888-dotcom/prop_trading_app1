import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field, validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, get_redis
from models import (
    Account, AccountStatus, CloseReason, Trade, TradeDirection,
    TradeStatus
)
from routers.auth import get_current_user
from services.pnl_calculator import (
    calculate_equity,
    calculate_position_size_from_risk,
    calculate_trade_pnl,
)
from services.price_feed import SUPPORTED_SYMBOLS, fetch_all_prices, fetch_price_rest
from services.risk_manager import (
    check_and_update_day_start,
    check_drawdown_rules,
    check_phase_completion,
    fail_account,
    update_peak_equity,
    update_trading_days,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/trading", tags=["trading"])

SYMBOL_DISPLAY_MAP = {
    "BTCUSDT": "BTC/USDT",
    "ETHUSDT": "ETH/USDT",
    "SOLUSDT": "SOL/USDT",
    "BNBUSDT": "BNB/USDT",
    "XRPUSDT": "XRP/USDT",
    "DOGEUSDT": "DOGE/USDT",
    "TONUSDT": "TON/USDT",
}


class OpenTradeRequest(BaseModel):
    symbol: str = Field(..., description="e.g. BTCUSDT")
    direction: TradeDirection
    leverage: int = Field(..., ge=1, le=10)
    risk_pct: Decimal = Field(..., ge=Decimal("0.1"), le=Decimal("10"))
    take_profit: Decimal = Field(..., gt=0)
    stop_loss: Decimal = Field(..., gt=0)

    @validator("symbol")
    def validate_symbol(cls, v):
        if v not in SUPPORTED_SYMBOLS:
            raise ValueError(f"Неподдерживаемый символ. Доступны: {', '.join(SUPPORTED_SYMBOLS)}")
        return v


class CloseTradeRequest(BaseModel):
    trade_id: int


class TradeResponse(BaseModel):
    id: int
    symbol: str
    direction: str
    status: str
    leverage: int
    position_size: str
    notional_value: str
    margin_used: str
    entry_price: str
    take_profit: str
    stop_loss: str
    close_price: Optional[str]
    realized_pnl: Optional[str]
    close_reason: Optional[str]
    opened_at: str
    closed_at: Optional[str]
    unrealized_pnl: Optional[str] = None


class PricesResponse(BaseModel):
    prices: dict


def _format_trade(trade: Trade, current_price: Optional[Decimal] = None) -> TradeResponse:
    unrealized = None
    if trade.status == TradeStatus.OPEN and current_price is not None:
        from services.pnl_calculator import calculate_unrealized_pnl
        unrealized = str(calculate_unrealized_pnl(trade, current_price))

    return TradeResponse(
        id=trade.id,
        symbol=trade.symbol,
        direction=trade.direction.value,
        status=trade.status.value,
        leverage=trade.leverage,
        position_size=str(trade.position_size),
        notional_value=str(trade.notional_value),
        margin_used=str(trade.margin_used),
        entry_price=str(trade.entry_price),
        take_profit=str(trade.take_profit),
        stop_loss=str(trade.stop_loss),
        close_price=str(trade.close_price) if trade.close_price else None,
        realized_pnl=str(trade.realized_pnl) if trade.realized_pnl is not None else None,
        close_reason=trade.close_reason.value if trade.close_reason else None,
        opened_at=trade.opened_at.isoformat(),
        closed_at=trade.closed_at.isoformat() if trade.closed_at else None,
        unrealized_pnl=unrealized,
    )


@router.get("/prices", response_model=PricesResponse)
async def get_prices():
    """Получить текущие цены всех поддерживаемых пар."""
    prices = await fetch_all_prices()
    return PricesResponse(prices={k: str(v) for k, v in prices.items()})


@router.post("/open", response_model=TradeResponse)
async def open_trade(
    body: OpenTradeRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user, account = await get_current_user(token, db)

    if account.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Аккаунт имеет статус {account.status.value}. Торговля недоступна.",
        )

    await check_and_update_day_start(account, db)

    # Получаем актуальную цену
    entry_price = await fetch_price_rest(body.symbol)

    # Валидируем TP/SL относительно направления
    if body.direction == TradeDirection.LONG:
        if body.take_profit <= entry_price:
            raise HTTPException(status_code=400, detail="Take Profit должен быть выше цены входа для LONG")
        if body.stop_loss >= entry_price:
            raise HTTPException(status_code=400, detail="Stop Loss должен быть ниже цены входа для LONG")
    else:
        if body.take_profit >= entry_price:
            raise HTTPException(status_code=400, detail="Take Profit должен быть ниже цены входа для SHORT")
        if body.stop_loss <= entry_price:
            raise HTTPException(status_code=400, detail="Stop Loss должен быть выше цены входа для SHORT")

    balance = Decimal(str(account.current_balance))

    try:
        size_data = calculate_position_size_from_risk(
            balance=balance,
            risk_pct=body.risk_pct,
            entry_price=entry_price,
            stop_loss=body.stop_loss,
            direction=body.direction,
            leverage=body.leverage,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Проверяем достаточность маржи
    if size_data["margin_used"] > balance:
        raise HTTPException(status_code=400, detail="Недостаточно средств для открытия позиции")

    trade = Trade(
        account_id=account.id,
        symbol=body.symbol,
        direction=body.direction,
        status=TradeStatus.OPEN,
        leverage=body.leverage,
        position_size=size_data["position_size"],
        notional_value=size_data["notional_value"],
        margin_used=size_data["margin_used"],
        entry_price=entry_price,
        take_profit=body.take_profit,
        stop_loss=body.stop_loss,
    )
    db.add(trade)

    # Резервируем маржу (уменьшаем баланс)
    account.current_balance = (balance - size_data["margin_used"]).quantize(Decimal("0.01"))
    db.add(account)

    await db.commit()
    await db.refresh(trade)

    return _format_trade(trade, entry_price)


@router.post("/close", response_model=TradeResponse)
async def close_trade(
    body: CloseTradeRequest,
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user, account = await get_current_user(token, db)

    result = await db.execute(
        select(Trade).where(
            Trade.id == body.trade_id,
            Trade.account_id == account.id,
            Trade.status == TradeStatus.OPEN,
        )
    )
    trade = result.scalar_one_or_none()

    if not trade:
        raise HTTPException(status_code=404, detail="Открытая сделка не найдена")

    close_price = await fetch_price_rest(trade.symbol)

    pnl = calculate_trade_pnl(
        direction=trade.direction,
        entry_price=Decimal(str(trade.entry_price)),
        close_price=close_price,
        position_size=Decimal(str(trade.position_size)),
        leverage=trade.leverage,
    )

    now = datetime.now(timezone.utc)
    trade.close_price = close_price
    trade.realized_pnl = pnl
    trade.close_reason = CloseReason.MANUAL
    trade.status = TradeStatus.CLOSED
    trade.closed_at = now
    db.add(trade)

    # Возвращаем маржу + PnL
    margin = Decimal(str(trade.margin_used))
    new_balance = (Decimal(str(account.current_balance)) + margin + pnl).quantize(Decimal("0.01"))
    account.current_balance = new_balance
    account.total_trades += 1
    if pnl > 0:
        account.winning_trades += 1
    db.add(account)

    await update_trading_days(account, db)

    # Обновляем peak equity
    all_open_result = await db.execute(
        select(Trade).where(Trade.account_id == account.id, Trade.status == TradeStatus.OPEN)
    )
    open_trades = all_open_result.scalars().all()
    prices = await fetch_all_prices()
    equity = calculate_equity(account, open_trades, prices)
    await update_peak_equity(account, equity, db)

    # Проверяем правила просадки
    violated, fail_reason, detail = await check_drawdown_rules(account, equity)
    if violated:
        await fail_account(account, fail_reason, detail, db, open_trades, prices)
        await db.commit()
        await db.refresh(trade)

        # Отправляем уведомление через бот
        await _notify_fail(user.id, account, detail)
        return _format_trade(trade, close_price)

    # Проверяем завершение фазы
    phase_passed = await check_phase_completion(account, db)
    await db.commit()
    await db.refresh(trade)

    if phase_passed:
        await _notify_phase_change(user.id, account)
    else:
        await _notify_trade_closed(user.id, trade)

    return _format_trade(trade, close_price)


@router.get("/open", response_model=List[TradeResponse])
async def get_open_trades(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user, account = await get_current_user(token, db)

    result = await db.execute(
        select(Trade).where(
            Trade.account_id == account.id,
            Trade.status == TradeStatus.OPEN,
        ).order_by(Trade.opened_at.desc())
    )
    trades = result.scalars().all()
    prices = await fetch_all_prices()

    return [
        _format_trade(t, prices.get(t.symbol))
        for t in trades
    ]


@router.post("/check-tpsl")
async def check_tpsl_all(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Проверяет достижение TP/SL для всех открытых позиций аккаунта.
    Вызывается фронтендом при получении обновления цены.
    """
    token = authorization.replace("Bearer ", "")
    user, account = await get_current_user(token, db)

    if account.status != AccountStatus.ACTIVE:
        return {"closed": []}

    await check_and_update_day_start(account, db)

    result = await db.execute(
        select(Trade).where(
            Trade.account_id == account.id,
            Trade.status == TradeStatus.OPEN,
        )
    )
    open_trades = result.scalars().all()

    if not open_trades:
        return {"closed": []}

    prices = await fetch_all_prices()
    closed_trades = []
    now = datetime.now(timezone.utc)

    for trade in open_trades:
        price = prices.get(trade.symbol)
        if price is None:
            continue
        price = Decimal(str(price))

        tp = Decimal(str(trade.take_profit))
        sl = Decimal(str(trade.stop_loss))
        direction = trade.direction

        hit_tp = (direction == TradeDirection.LONG and price >= tp) or \
                 (direction == TradeDirection.SHORT and price <= tp)
        hit_sl = (direction == TradeDirection.LONG and price <= sl) or \
                 (direction == TradeDirection.SHORT and price >= sl)

        if not (hit_tp or hit_sl):
            continue

        close_price = tp if hit_tp else sl
        close_reason = CloseReason.TAKE_PROFIT if hit_tp else CloseReason.STOP_LOSS

        pnl = calculate_trade_pnl(
            direction=direction,
            entry_price=Decimal(str(trade.entry_price)),
            close_price=close_price,
            position_size=Decimal(str(trade.position_size)),
            leverage=trade.leverage,
        )

        trade.close_price = close_price
        trade.realized_pnl = pnl
        trade.close_reason = close_reason
        trade.status = TradeStatus.CLOSED
        trade.closed_at = now
        db.add(trade)

        margin = Decimal(str(trade.margin_used))
        account.current_balance = (
            Decimal(str(account.current_balance)) + margin + pnl
        ).quantize(Decimal("0.01"))
        account.total_trades += 1
        if pnl > 0:
            account.winning_trades += 1
        db.add(account)

        await update_trading_days(account, db)
        closed_trades.append(_format_trade(trade, close_price))
        await _notify_trade_closed(user.id, trade)

    # После закрытия позиций проверяем просадку
    remaining_open = await db.execute(
        select(Trade).where(Trade.account_id == account.id, Trade.status == TradeStatus.OPEN)
    )
    remaining = remaining_open.scalars().all()
    equity = calculate_equity(account, remaining, prices)
    await update_peak_equity(account, equity, db)

    violated, fail_reason, detail = await check_drawdown_rules(account, equity)
    if violated:
        await fail_account(account, fail_reason, detail, db, remaining, prices)
        await _notify_fail(user.id, account, detail)

    if not violated:
        phase_passed = await check_phase_completion(account, db)
        if phase_passed:
            await _notify_phase_change(user.id, account)

    await db.commit()
    return {"closed": closed_trades}


async def _notify_trade_closed(user_id: int, trade: Trade):
    """Отправляем уведомление в бот о закрытии сделки."""
    try:
        from database import get_redis
        redis = await get_redis()
        import json
        payload = json.dumps({
            "type": "trade_closed",
            "user_id": user_id,
            "symbol": trade.symbol,
            "direction": trade.direction.value,
            "pnl": str(trade.realized_pnl),
            "close_reason": trade.close_reason.value if trade.close_reason else "MANUAL",
        })
        await redis.lpush("bot_notifications", payload)
    except Exception as e:
        logger.error(f"Failed to queue trade notification: {e}")


async def _notify_phase_change(user_id: int, account: Account):
    try:
        from database import get_redis
        redis = await get_redis()
        import json
        payload = json.dumps({
            "type": "phase_changed",
            "user_id": user_id,
            "new_phase": account.phase.value,
        })
        await redis.lpush("bot_notifications", payload)
    except Exception as e:
        logger.error(f"Failed to queue phase notification: {e}")


async def _notify_fail(user_id: int, account: Account, detail: str):
    try:
        from database import get_redis
        redis = await get_redis()
        import json
        payload = json.dumps({
            "type": "account_failed",
            "user_id": user_id,
            "reason": account.fail_reason.value if account.fail_reason else "UNKNOWN",
            "detail": detail,
        })
        await redis.lpush("bot_notifications", payload)
    except Exception as e:
        logger.error(f"Failed to queue fail notification: {e}")
