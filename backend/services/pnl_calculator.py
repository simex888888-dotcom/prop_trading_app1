from decimal import Decimal
from typing import List, Optional

from models import Account, Trade, TradeDirection


def calculate_trade_pnl(
    direction: TradeDirection,
    entry_price: Decimal,
    close_price: Decimal,
    position_size: Decimal,
    leverage: int,
) -> Decimal:
    """
    PnL = (close - entry) * direction_multiplier * position_size * leverage
    position_size — в базовой валюте (BTC, ETH и т.д.)
    Результат в USDT.
    """
    direction_multiplier = Decimal("1") if direction == TradeDirection.LONG else Decimal("-1")
    pnl = (close_price - entry_price) * direction_multiplier * position_size
    return pnl.quantize(Decimal("0.01"))


def calculate_unrealized_pnl(trade: Trade, current_price: Decimal) -> Decimal:
    return calculate_trade_pnl(
        direction=trade.direction,
        entry_price=Decimal(str(trade.entry_price)),
        close_price=current_price,
        position_size=Decimal(str(trade.position_size)),
        leverage=trade.leverage,
    )


def calculate_equity(account: Account, open_trades: List[Trade], prices: dict) -> Decimal:
    """Equity = balance + sum(unrealized PnL для каждой открытой позиции)."""
    balance = Decimal(str(account.current_balance))
    unrealized_total = Decimal("0")

    for trade in open_trades:
        symbol = trade.symbol
        price = prices.get(symbol)
        if price is not None:
            unrealized_total += calculate_unrealized_pnl(trade, Decimal(str(price)))

    return (balance + unrealized_total).quantize(Decimal("0.01"))


def calculate_daily_drawdown_pct(equity: Decimal, day_start_balance: Decimal) -> Decimal:
    """
    Дневная просадка = (equity - day_start_balance) / day_start_balance * 100
    Отрицательное значение = просадка.
    """
    if day_start_balance == Decimal("0"):
        return Decimal("0")
    return ((equity - day_start_balance) / day_start_balance * Decimal("100")).quantize(Decimal("0.01"))


def calculate_trailing_drawdown_pct(equity: Decimal, peak_equity: Decimal) -> Decimal:
    """
    Trailing drawdown = (peak_equity - equity) / peak_equity * 100
    Положительное значение = просадка от пика.
    """
    if peak_equity == Decimal("0"):
        return Decimal("0")
    return ((peak_equity - equity) / peak_equity * Decimal("100")).quantize(Decimal("0.01"))


def calculate_profit_progress_pct(account: Account) -> Decimal:
    """Прогресс к цели прибыли в процентах от начального баланса."""
    initial = Decimal(str(account.initial_balance))
    current = Decimal(str(account.current_balance))
    if initial == Decimal("0"):
        return Decimal("0")
    profit_pct = (current - initial) / initial * Decimal("100")
    target = Decimal(str(account.profit_target_pct))
    if target == Decimal("0"):
        return Decimal("100")
    progress = (profit_pct / target * Decimal("100")).quantize(Decimal("0.01"))
    return min(progress, Decimal("100"))


def calculate_win_rate(total_trades: int, winning_trades: int) -> Decimal:
    if total_trades == 0:
        return Decimal("0")
    return (Decimal(winning_trades) / Decimal(total_trades) * Decimal("100")).quantize(Decimal("0.01"))


def calculate_position_size_from_risk(
    balance: Decimal,
    risk_pct: Decimal,
    entry_price: Decimal,
    stop_loss: Decimal,
    direction: TradeDirection,
    leverage: int,
) -> dict:
    """
    Рассчитывает размер позиции исходя из процента риска от депозита.

    risk_pct — процент баланса, которым рискует трейдер (например, 1.0 = 1%)
    Возвращает: position_size (в базовой валюте), notional_value (USDT), margin_used (USDT)
    """
    risk_amount = balance * risk_pct / Decimal("100")

    # Расстояние до стопа в USDT за единицу базовой валюты
    if direction == TradeDirection.LONG:
        stop_distance = entry_price - stop_loss
    else:
        stop_distance = stop_loss - entry_price

    if stop_distance <= Decimal("0"):
        raise ValueError("Stop loss не корректен для выбранного направления")

    # position_size = risk_amount / stop_distance
    position_size = risk_amount / stop_distance
    notional_value = position_size * entry_price
    margin_used = notional_value / Decimal(str(leverage))

    return {
        "position_size": position_size.quantize(Decimal("0.00000001")),
        "notional_value": notional_value.quantize(Decimal("0.01")),
        "margin_used": margin_used.quantize(Decimal("0.01")),
    }
