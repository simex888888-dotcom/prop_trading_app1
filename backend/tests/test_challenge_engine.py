"""
Тесты для ChallengeEngine — главного движка проверки правил CHM_KRYPTON.

Покрывает:
- Расчёт дневной просадки (статической)
- Расчёт общей просадки (статической и trailing)
- Обнаружение нарушений (daily_loss, total_loss, consistency, max_days)
- Дневной сброс баланса
- Проверку правила консистентности
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.challenge_engine import ChallengeEngine
from app.models.violation import ViolationType


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_challenge_type(
    max_daily_loss: float = 5.0,
    max_total_loss: float = 10.0,
    profit_target_p1: float = 8.0,
    profit_target_p2: float = 5.0,
    drawdown_type: str = "static",
    consistency_rule: bool = False,
    max_trading_days: int | None = None,
) -> MagicMock:
    ct = MagicMock()
    ct.max_daily_loss = Decimal(str(max_daily_loss))
    ct.max_total_loss = Decimal(str(max_total_loss))
    ct.profit_target_p1 = Decimal(str(profit_target_p1))
    ct.profit_target_p2 = Decimal(str(profit_target_p2))
    ct.drawdown_type = drawdown_type
    ct.consistency_rule = consistency_rule
    ct.max_trading_days = max_trading_days
    ct.news_trading_ban = False
    return ct


def make_challenge(
    initial_balance: float = 10_000.0,
    daily_start_balance: float | None = None,
    peak_equity: float | None = None,
    total_pnl: float = 0.0,
    daily_pnl: float = 0.0,
    trading_days_count: int = 0,
    status: str = "phase1",
    daily_reset_at: datetime | None = None,
) -> MagicMock:
    ch = MagicMock()
    ch.id = 1
    ch.user_id = 42
    ch.initial_balance = Decimal(str(initial_balance))
    ch.daily_start_balance = Decimal(str(daily_start_balance or initial_balance))
    ch.peak_equity = Decimal(str(peak_equity or initial_balance))
    ch.total_pnl = Decimal(str(total_pnl))
    ch.daily_pnl = Decimal(str(daily_pnl))
    ch.trading_days_count = trading_days_count
    ch.status = status
    ch.daily_reset_at = daily_reset_at
    ch.account_mode = "demo"
    ch.challenge_type = make_challenge_type()
    return ch


def make_engine() -> ChallengeEngine:
    """Создаёт ChallengeEngine с замоканной сессией и уведомлениями."""
    session = AsyncMock()
    engine = ChallengeEngine.__new__(ChallengeEngine)
    engine.session = session
    engine.notification_service = AsyncMock()
    engine.master_client = AsyncMock()
    return engine


# ── _calc_daily_drawdown ─────────────────────────────────────────────────────

class TestCalcDailyDrawdown:
    def test_no_loss_returns_zero(self):
        engine = make_engine()
        ch = make_challenge(initial_balance=10_000, daily_start_balance=10_000)
        equity = Decimal("10_500")
        result = engine._calc_daily_drawdown(ch, equity)
        assert result == Decimal("0")

    def test_exact_limit(self):
        """5% дневной убыток при лимите 5% — должно дать 5%."""
        engine = make_engine()
        ch = make_challenge(daily_start_balance=10_000)
        equity = Decimal("9500")  # -$500 = -5%
        result = engine._calc_daily_drawdown(ch, equity)
        assert result == Decimal("5")

    def test_partial_loss(self):
        engine = make_engine()
        ch = make_challenge(daily_start_balance=10_000)
        equity = Decimal("9750")  # -$250 = -2.5%
        result = engine._calc_daily_drawdown(ch, equity)
        assert result == Decimal("2.5")

    def test_zero_daily_start_balance(self):
        """Деление на 0 должно вернуть 0, не выбросить исключение."""
        engine = make_engine()
        ch = make_challenge()
        ch.daily_start_balance = Decimal("0")
        result = engine._calc_daily_drawdown(ch, Decimal("100"))
        assert result == Decimal("0")

    def test_larger_loss(self):
        engine = make_engine()
        ch = make_challenge(daily_start_balance=20_000)
        equity = Decimal("18000")  # -$2000 = -10%
        result = engine._calc_daily_drawdown(ch, equity)
        assert result == Decimal("10")


# ── _calc_total_drawdown ─────────────────────────────────────────────────────

class TestCalcTotalDrawdown:
    def test_static_no_loss(self):
        engine = make_engine()
        ct = make_challenge_type(drawdown_type="static")
        ch = make_challenge(initial_balance=10_000, peak_equity=10_000)
        result = engine._calc_total_drawdown(ch, ct, Decimal("10500"))
        assert result == Decimal("0")

    def test_static_loss(self):
        engine = make_engine()
        ct = make_challenge_type(drawdown_type="static")
        ch = make_challenge(initial_balance=10_000)
        equity = Decimal("9000")  # -$1000 = -10%
        result = engine._calc_total_drawdown(ch, ct, equity)
        assert result == Decimal("10")

    def test_trailing_from_peak(self):
        """Trailing drawdown считается от пика, не от начального баланса."""
        engine = make_engine()
        ct = make_challenge_type(drawdown_type="trailing")
        ch = make_challenge(initial_balance=10_000, peak_equity=12_000)
        equity = Decimal("10800")  # -$1200 from peak = -10%
        result = engine._calc_total_drawdown(ch, ct, equity)
        assert result == Decimal("10")

    def test_trailing_no_loss_above_peak(self):
        engine = make_engine()
        ct = make_challenge_type(drawdown_type="trailing")
        ch = make_challenge(peak_equity=10_000)
        equity = Decimal("11_000")  # above peak → 0
        result = engine._calc_total_drawdown(ch, ct, equity)
        assert result == Decimal("0")

    def test_zero_base(self):
        engine = make_engine()
        ct = make_challenge_type(drawdown_type="static")
        ch = make_challenge()
        ch.initial_balance = Decimal("0")
        result = engine._calc_total_drawdown(ch, ct, Decimal("100"))
        assert result == Decimal("0")


# ── _check_violations ────────────────────────────────────────────────────────

class TestCheckViolations:
    @pytest.mark.asyncio
    async def test_daily_loss_violation(self):
        engine = make_engine()
        ct = make_challenge_type(max_daily_loss=5.0)
        ch = make_challenge()
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("5.1"), Decimal("3"), now)
        assert result is not None
        assert result["type"] == ViolationType.daily_loss
        assert result["value"] == Decimal("5.1")
        assert result["limit"] == Decimal("5")

    @pytest.mark.asyncio
    async def test_total_loss_violation(self):
        engine = make_engine()
        ct = make_challenge_type(max_total_loss=10.0)
        ch = make_challenge()
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("4"), Decimal("10.5"), now)
        assert result is not None
        assert result["type"] == ViolationType.total_loss
        assert result["value"] == Decimal("10.5")

    @pytest.mark.asyncio
    async def test_daily_loss_takes_priority_over_total(self):
        """Нарушение дневного лимита имеет приоритет."""
        engine = make_engine()
        ct = make_challenge_type(max_daily_loss=5.0, max_total_loss=10.0)
        ch = make_challenge()
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("6"), Decimal("11"), now)
        assert result["type"] == ViolationType.daily_loss

    @pytest.mark.asyncio
    async def test_no_violation_below_limits(self):
        engine = make_engine()
        ct = make_challenge_type(max_daily_loss=5.0, max_total_loss=10.0)
        ch = make_challenge()
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("3"), Decimal("7"), now)
        assert result is None

    @pytest.mark.asyncio
    async def test_max_trading_days_violation(self):
        engine = make_engine()
        ct = make_challenge_type(max_trading_days=30)
        ch = make_challenge(trading_days_count=31)
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("1"), Decimal("2"), now)
        assert result is not None
        assert result["type"] == ViolationType.max_trading_days

    @pytest.mark.asyncio
    async def test_max_trading_days_not_exceeded(self):
        engine = make_engine()
        ct = make_challenge_type(max_trading_days=30)
        ch = make_challenge(trading_days_count=29)
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("1"), Decimal("2"), now)
        assert result is None

    @pytest.mark.asyncio
    async def test_max_trading_days_none_skipped(self):
        """Если max_trading_days не задан — проверка не выполняется."""
        engine = make_engine()
        ct = make_challenge_type(max_trading_days=None)
        ch = make_challenge(trading_days_count=999)
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("0"), Decimal("0"), now)
        assert result is None

    @pytest.mark.asyncio
    async def test_consistency_rule_triggered(self):
        engine = make_engine()
        ct = make_challenge_type(consistency_rule=True)
        ch = make_challenge(total_pnl=1000)

        # today_pnl = $400 > 30% of $1000 = $300 → violation
        trade = MagicMock()
        trade.pnl = Decimal("400")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [trade]
        engine.session.execute = AsyncMock(return_value=mock_result)

        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("0"), Decimal("0"), now)
        assert result is not None
        assert result["type"] == ViolationType.consistency

    @pytest.mark.asyncio
    async def test_consistency_rule_not_triggered_below_30pct(self):
        engine = make_engine()
        ct = make_challenge_type(consistency_rule=True)
        ch = make_challenge(total_pnl=1000)

        trade = MagicMock()
        trade.pnl = Decimal("250")  # 25% < 30% → OK
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [trade]
        engine.session.execute = AsyncMock(return_value=mock_result)

        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("0"), Decimal("0"), now)
        assert result is None

    @pytest.mark.asyncio
    async def test_consistency_rule_skipped_when_no_profit(self):
        """Правило консистентности не проверяется при нулевой прибыли."""
        engine = make_engine()
        ct = make_challenge_type(consistency_rule=True)
        ch = make_challenge(total_pnl=0)
        now = datetime.now(timezone.utc)
        # session.execute should NOT be called for consistency check
        engine.session.execute = AsyncMock()
        result = await engine._check_violations(ch, ct, Decimal("0"), Decimal("0"), now)
        assert result is None


# ── _daily_reset_check ───────────────────────────────────────────────────────

class TestDailyResetCheck:
    @pytest.mark.asyncio
    async def test_first_run_sets_reset_at(self):
        engine = make_engine()
        ch = make_challenge()
        ch.daily_reset_at = None
        now = datetime.now(timezone.utc)
        await engine._daily_reset_check(ch, Decimal("10000"), now)
        assert ch.daily_reset_at == now
        assert ch.daily_start_balance == Decimal("10000")

    @pytest.mark.asyncio
    async def test_same_day_no_reset(self):
        engine = make_engine()
        ch = make_challenge(daily_start_balance=10_000)
        yesterday = datetime.now(timezone.utc)
        ch.daily_reset_at = yesterday
        ch.daily_start_balance = Decimal("10000")

        # Still same day
        now = yesterday.replace(hour=(yesterday.hour + 1) % 24)
        original_balance = ch.daily_start_balance
        await engine._daily_reset_check(ch, Decimal("9500"), now)
        # Balance should NOT change
        assert ch.daily_start_balance == original_balance

    @pytest.mark.asyncio
    async def test_new_day_triggers_reset(self):
        engine = make_engine()
        ch = make_challenge()
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        ch.daily_reset_at = yesterday
        ch.daily_start_balance = Decimal("10000")

        now = datetime.now(timezone.utc)
        await engine._daily_reset_check(ch, Decimal("10300"), now)
        # Should reset to current balance
        assert ch.daily_start_balance == Decimal("10300")
        assert ch.daily_pnl == Decimal("0")


# ── _check_consistency_rule ──────────────────────────────────────────────────

class TestCheckConsistencyRule:
    @pytest.mark.asyncio
    async def test_returns_none_when_total_pnl_zero(self):
        engine = make_engine()
        ch = make_challenge(total_pnl=0)
        result = await engine._check_consistency_rule(ch)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_total_pnl_negative(self):
        engine = make_engine()
        ch = make_challenge(total_pnl=-100)
        result = await engine._check_consistency_rule(ch)
        assert result is None

    @pytest.mark.asyncio
    async def test_violation_when_single_day_exceeds_30pct(self):
        engine = make_engine()
        ch = make_challenge(total_pnl=2000)

        # Day PnL = $700 → 35% > 30% → violation
        t1 = MagicMock(); t1.pnl = Decimal("400")
        t2 = MagicMock(); t2.pnl = Decimal("300")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [t1, t2]
        engine.session.execute = AsyncMock(return_value=mock_result)

        result = await engine._check_consistency_rule(ch)
        assert result is not None
        assert result["type"] == ViolationType.consistency

    @pytest.mark.asyncio
    async def test_no_violation_exact_30pct(self):
        engine = make_engine()
        ch = make_challenge(total_pnl=1000)

        trade = MagicMock(); trade.pnl = Decimal("300")  # exactly 30%
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [trade]
        engine.session.execute = AsyncMock(return_value=mock_result)

        result = await engine._check_consistency_rule(ch)
        # Exactly 30% should NOT trigger (only > 30%)
        assert result is None

    @pytest.mark.asyncio
    async def test_no_violation_no_trades_today(self):
        engine = make_engine()
        ch = make_challenge(total_pnl=5000)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        engine.session.execute = AsyncMock(return_value=mock_result)

        result = await engine._check_consistency_rule(ch)
        assert result is None


# ── Drawdown edge cases ──────────────────────────────────────────────────────

class TestDrawdownEdgeCases:
    def test_profit_returns_zero_daily_drawdown(self):
        """Прибыльный день не имеет просадки."""
        engine = make_engine()
        ch = make_challenge(daily_start_balance=10_000)
        equity = Decimal("10500")  # +$500 profit
        result = engine._calc_daily_drawdown(ch, equity)
        assert result == Decimal("0")

    def test_trailing_drawdown_updates_on_new_peak(self):
        """
        При trailing drawdown: если peak_equity = 12_000 и equity = 11_500,
        то drawdown = (12000 - 11500) / 12000 * 100 = 4.17%
        """
        engine = make_engine()
        ct = make_challenge_type(drawdown_type="trailing")
        ch = make_challenge(initial_balance=10_000, peak_equity=12_000)
        equity = Decimal("11500")
        result = engine._calc_total_drawdown(ch, ct, equity)
        expected = (Decimal("12000") - Decimal("11500")) / Decimal("12000") * 100
        assert abs(result - expected) < Decimal("0.01")

    def test_static_drawdown_ignores_peak(self):
        """
        Static drawdown: всегда от initial_balance, не от peak_equity.
        Даже если peak > initial, base = initial.
        """
        engine = make_engine()
        ct = make_challenge_type(drawdown_type="static")
        ch = make_challenge(initial_balance=10_000, peak_equity=15_000)
        equity = Decimal("9_000")  # -10% from 10_000
        result = engine._calc_total_drawdown(ch, ct, equity)
        assert result == Decimal("10")


# ── Violation threshold precision ────────────────────────────────────────────

class TestViolationThresholds:
    @pytest.mark.asyncio
    async def test_daily_loss_exactly_at_limit_triggers(self):
        """Просадка ровно на уровне лимита должна считаться нарушением (>=)."""
        engine = make_engine()
        ct = make_challenge_type(max_daily_loss=5.0)
        ch = make_challenge()
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("5.0"), Decimal("0"), now)
        assert result is not None
        assert result["type"] == ViolationType.daily_loss

    @pytest.mark.asyncio
    async def test_daily_loss_just_below_limit_no_violation(self):
        """Просадка чуть ниже лимита не должна быть нарушением."""
        engine = make_engine()
        ct = make_challenge_type(max_daily_loss=5.0)
        ch = make_challenge()
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("4.99"), Decimal("0"), now)
        assert result is None

    @pytest.mark.asyncio
    async def test_total_loss_exactly_at_limit_triggers(self):
        engine = make_engine()
        ct = make_challenge_type(max_total_loss=10.0)
        ch = make_challenge()
        now = datetime.now(timezone.utc)
        result = await engine._check_violations(ch, ct, Decimal("0"), Decimal("10.0"), now)
        assert result is not None
        assert result["type"] == ViolationType.total_loss
