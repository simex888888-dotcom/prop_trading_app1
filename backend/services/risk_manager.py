import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Account, AccountPhase, AccountStatus, CloseReason, FailReason,
    Trade, TradeStatus
)
from services.pnl_calculator import (
    calculate_daily_drawdown_pct,
    calculate_equity,
    calculate_trailing_drawdown_pct,
)

logger = logging.getLogger(__name__)


async def check_and_update_day_start(account: Account, db: AsyncSession) -> None:
    """
    Если наступил новый UTC-день — обновляем day_start_balance.
    Вызывается при каждом обращении к аккаунту.
    """
    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    if account.day_start_date is None or account.day_start_date < today_start:
        account.day_start_balance = account.current_balance
        account.day_start_date = today_start
        db.add(account)


async def check_drawdown_rules(
    account: Account,
    equity: Decimal,
) -> Tuple[bool, Optional[FailReason], Optional[str]]:
    """
    Проверяет правила просадки.
    Возвращает (violated, fail_reason, detail_message).
    """
    day_start = Decimal(str(account.day_start_balance))
    peak = Decimal(str(account.peak_equity))

    daily_dd = calculate_daily_drawdown_pct(equity, day_start)
    trailing_dd = calculate_trailing_drawdown_pct(equity, peak)

    max_daily = Decimal(str(account.max_daily_drawdown_pct))
    max_trailing = Decimal(str(account.max_trailing_drawdown_pct))

    # Дневная просадка: если equity упала ниже -max_daily% от начала дня
    if daily_dd <= -max_daily:
        detail = (
            f"Дневная просадка {daily_dd:.2f}% превысила лимит -{max_daily:.2f}%. "
            f"Баланс начала дня: ${day_start:.2f}, текущий equity: ${equity:.2f}."
        )
        return True, FailReason.DAILY_DRAWDOWN_EXCEEDED, detail

    # Trailing drawdown: если equity упала на max_trailing% от пикового значения
    if trailing_dd >= max_trailing:
        detail = (
            f"Trailing просадка {trailing_dd:.2f}% превысила лимит {max_trailing:.2f}%. "
            f"Пиковый equity: ${peak:.2f}, текущий equity: ${equity:.2f}."
        )
        return True, FailReason.TRAILING_DRAWDOWN_EXCEEDED, detail

    return False, None, None


async def fail_account(
    account: Account,
    fail_reason: FailReason,
    detail: str,
    db: AsyncSession,
    open_trades: List[Trade],
    prices: dict,
) -> None:
    """Переводит аккаунт в статус FAILED и закрывает все открытые позиции."""
    now = datetime.now(timezone.utc)
    account.status = AccountStatus.FAILED
    account.fail_reason = fail_reason
    account.fail_detail = detail
    account.failed_at = now

    close_reason = (
        CloseReason.DAILY_DRAWDOWN
        if fail_reason == FailReason.DAILY_DRAWDOWN_EXCEEDED
        else CloseReason.TRAILING_DRAWDOWN
    )

    from services.pnl_calculator import calculate_trade_pnl
    from decimal import Decimal as D

    for trade in open_trades:
        price = prices.get(trade.symbol)
        if price is None:
            continue
        price = D(str(price))
        pnl = calculate_trade_pnl(
            direction=trade.direction,
            entry_price=D(str(trade.entry_price)),
            close_price=price,
            position_size=D(str(trade.position_size)),
            leverage=trade.leverage,
        )
        trade.close_price = price
        trade.realized_pnl = pnl
        trade.close_reason = close_reason
        trade.status = TradeStatus.CLOSED
        trade.closed_at = now
        account.current_balance = (D(str(account.current_balance)) + pnl).quantize(D("0.01"))
        if pnl > 0:
            account.winning_trades += 1
        account.total_trades += 1
        db.add(trade)

    db.add(account)
    logger.warning(f"Account {account.id} FAILED: {fail_reason.value} — {detail}")


async def check_phase_completion(account: Account, db: AsyncSession) -> bool:
    """
    Проверяет, выполнены ли условия перехода на следующую фазу.
    Возвращает True если фаза пройдена.
    """
    initial = Decimal(str(account.initial_balance))
    current = Decimal(str(account.current_balance))
    target_pct = Decimal(str(account.profit_target_pct))
    target_balance = initial * (1 + target_pct / Decimal("100"))

    days_ok = account.trading_days_count >= account.min_trading_days
    profit_ok = current >= target_balance

    if not (days_ok and profit_ok):
        return False

    now = datetime.now(timezone.utc)

    if account.phase == AccountPhase.EVALUATION:
        account.phase = AccountPhase.VERIFICATION
        account.status = AccountStatus.ACTIVE
        account.initial_balance = Decimal("10000.00")
        account.current_balance = Decimal("10000.00")
        account.peak_equity = Decimal("10000.00")
        account.day_start_balance = Decimal("10000.00")
        account.day_start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        account.profit_target_pct = Decimal("5.00")
        account.trading_days_count = 0
        account.total_trades = 0
        account.winning_trades = 0
        account.phase_passed_at = now
        db.add(account)
        logger.info(f"Account {account.id} moved to VERIFICATION phase")
        return True

    if account.phase == AccountPhase.VERIFICATION:
        account.phase = AccountPhase.FUNDED
        account.status = AccountStatus.ACTIVE
        account.profit_split_pct = Decimal("80.00")
        account.phase_passed_at = now
        db.add(account)
        logger.info(f"Account {account.id} moved to FUNDED phase")
        return True

    return False


async def update_peak_equity(account: Account, equity: Decimal, db: AsyncSession) -> None:
    """Обновляет пиковый equity если текущий выше."""
    peak = Decimal(str(account.peak_equity))
    if equity > peak:
        account.peak_equity = equity
        db.add(account)


async def update_trading_days(account: Account, db: AsyncSession) -> None:
    """
    Увеличивает счётчик торговых дней.
    Вызывается при закрытии сделки — проверяет, что сегодня день ещё не посчитан.
    """
    from models import Trade, TradeStatus
    from sqlalchemy import func, cast
    from sqlalchemy.dialects.postgresql import DATE

    now_utc = datetime.now(timezone.utc)
    today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)

    # Проверяем, была ли сегодня уже закрытая сделка (кроме текущей)
    result = await db.execute(
        select(Trade).where(
            Trade.account_id == account.id,
            Trade.status == TradeStatus.CLOSED,
            Trade.closed_at >= today_start,
        ).limit(2)
    )
    closed_today = result.scalars().all()

    # Если это первая закрытая сделка сегодня — увеличиваем счётчик дней
    if len(closed_today) == 1:
        account.trading_days_count += 1
        db.add(account)
