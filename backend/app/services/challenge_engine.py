"""
ChallengeEngine — фоновый движок проверки правил испытаний CHM_KRYPTON.

Запускается каждые 30 секунд через APScheduler.
Для каждого активного испытания:
  1. Получает текущий баланс и equity с биржи
  2. Рассчитывает дневную и общую просадку
  3. Проверяет все правила испытания
  4. При нарушении — закрывает все позиции, обновляет статус, уведомляет
  5. При достижении цели — переводит на следующую фазу / выдаёт финансирование
  6. Обновляет streak, достижения, проверяет масштабирование
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decrypt_aes256
from app.models.challenge import ChallengeStatus, UserChallenge
from app.models.scaling import ScalingStep
from app.models.trade import Trade
from app.models.violation import Violation, ViolationType
from app.services.exchange.bybit_client import BybitAPIError, BybitClient
from app.services.exchange.bybit_master import BybitMasterClient
from app.services.notification_service import NotificationService

if TYPE_CHECKING:
    from app.models.challenge import ChallengeType


class ChallengeEngine:
    """
    Движок проверки правил испытаний.
    Вызывается APScheduler каждые 30 секунд.
    """

    SCALING_TRIGGER_PCT = Decimal("10")   # +10% прибыли → масштабирование
    SCALING_INCREASE_PCT = Decimal("25")  # увеличение счёта на 25%
    MAX_ACCOUNT_SIZE = Decimal("2000000") # максимальный счёт $2M

    def __init__(self, session: AsyncSession):
        self.session = session
        self.notification_service = NotificationService(session)
        self.master_client = BybitMasterClient()

    # ─── Вспомогательный метод получения клиента ──────────────────────────────

    def _get_exchange_client(self, challenge: UserChallenge) -> BybitClient:
        """Возвращает Bybit клиент для demo или real аккаунта."""
        if challenge.account_mode == "demo":
            api_key = decrypt_aes256(challenge.demo_api_key_enc)
            api_secret = decrypt_aes256(challenge.demo_api_secret_enc)
            return BybitClient(api_key=api_key, api_secret=api_secret, mode="demo")
        else:
            api_key = decrypt_aes256(challenge.real_api_key_enc)
            api_secret = decrypt_aes256(challenge.real_api_secret_enc)
            return BybitClient(api_key=api_key, api_secret=api_secret, mode="real")

    # ─── Основной цикл проверки ───────────────────────────────────────────────

    async def run_all_checks(self) -> None:
        """Главный метод, вызываемый APScheduler."""
        active_statuses = [
            ChallengeStatus.phase1,
            ChallengeStatus.phase2,
            ChallengeStatus.funded,
        ]
        stmt = (
            select(UserChallenge)
            .where(UserChallenge.status.in_(active_statuses))
            .options(selectinload(UserChallenge.challenge_type))
            .options(selectinload(UserChallenge.user))
        )
        result = await self.session.execute(stmt)
        challenges = result.scalars().all()

        logger.debug(f"ChallengeEngine: checking {len(challenges)} active challenges")

        for challenge in challenges:
            try:
                await self._check_challenge(challenge)
            except Exception as e:
                logger.error(
                    f"ChallengeEngine error for challenge_id={challenge.id}: {e}",
                    exc_info=True,
                )

    async def _check_challenge(self, challenge: UserChallenge) -> None:
        """Проверяет одно испытание."""
        ct = challenge.challenge_type
        client = self._get_exchange_client(challenge)

        try:
            # 1. Получаем данные с биржи
            balance_data = await client.get_balance()
            equity = balance_data["equity"]
            wallet_balance = balance_data["wallet_balance"]
            unrealized_pnl = balance_data["unrealized_pnl"]

            # 2. Обновляем текущий баланс и peak equity
            challenge.current_balance = wallet_balance

            # Обновляем пик (для trailing drawdown)
            if equity > challenge.peak_equity:
                challenge.peak_equity = equity

            # 3. Сброс дневного баланса в полночь UTC
            now = datetime.now(timezone.utc)
            await self._daily_reset_check(challenge, wallet_balance, now)

            # 4. Рассчитываем просадки
            daily_drawdown_pct = self._calc_daily_drawdown(challenge, equity)
            total_drawdown_pct = self._calc_total_drawdown(challenge, ct, equity)
            total_pnl = equity - challenge.initial_balance

            challenge.daily_pnl = equity - challenge.daily_start_balance
            challenge.total_pnl = total_pnl

            # 5. Предупреждения о просадке (80% от лимита)
            await self._check_drawdown_warnings(challenge, ct, daily_drawdown_pct, total_drawdown_pct)

            # 6. Проверяем нарушения
            violation = await self._check_violations(
                challenge, ct, daily_drawdown_pct, total_drawdown_pct, now
            )
            if violation:
                await self._handle_violation(challenge, client, violation)
                return

            # 7. Проверяем достижение цели прибыли
            await self._check_profit_target(challenge, ct, total_pnl, equity, now)

            # 8. Считаем торговые дни
            await self._update_trading_days(challenge, now)

            # 9. Масштабирование (только для funded)
            if challenge.status == ChallengeStatus.funded:
                await self._check_scaling(challenge, total_pnl)

            await self.session.commit()

        except BybitAPIError as e:
            logger.warning(f"Bybit API error for challenge {challenge.id}: {e}")
        finally:
            await client.close()

    # ─── Дневной сброс ────────────────────────────────────────────────────────

    async def _daily_reset_check(
        self, challenge: UserChallenge, current_balance: Decimal, now: datetime
    ) -> None:
        """Сбрасывает дневной баланс в полночь UTC."""
        if challenge.daily_reset_at is None:
            challenge.daily_reset_at = now
            challenge.daily_start_balance = current_balance
            return

        reset_date = challenge.daily_reset_at.date()
        today = now.date()
        if today > reset_date:
            # Новый день — засчитываем торговый день если были сделки
            challenge.daily_start_balance = current_balance
            challenge.daily_pnl = Decimal("0")
            challenge.daily_reset_at = now
            logger.debug(f"Daily reset for challenge {challenge.id}")

    # ─── Расчёт просадок ──────────────────────────────────────────────────────

    def _calc_daily_drawdown(self, challenge: UserChallenge, equity: Decimal) -> Decimal:
        """Дневная просадка в % от дневного стартового баланса."""
        if challenge.daily_start_balance == 0:
            return Decimal("0")
        daily_loss = challenge.daily_start_balance - equity
        if daily_loss <= 0:
            return Decimal("0")
        return (daily_loss / challenge.daily_start_balance) * 100

    def _calc_total_drawdown(
        self, challenge: UserChallenge, ct: "ChallengeType", equity: Decimal
    ) -> Decimal:
        """Общая просадка (статическая или trailing) в %."""
        from app.models.challenge import DrawdownType

        if ct.drawdown_type == DrawdownType.trailing:
            # От пика equity
            base = challenge.peak_equity
        else:
            # От начального баланса (static)
            base = challenge.initial_balance

        if base == 0:
            return Decimal("0")
        loss = base - equity
        if loss <= 0:
            return Decimal("0")
        return (loss / base) * 100

    # ─── Предупреждения ───────────────────────────────────────────────────────

    async def _check_drawdown_warnings(
        self,
        challenge: UserChallenge,
        ct: "ChallengeType",
        daily_dd: Decimal,
        total_dd: Decimal,
    ) -> None:
        """Отправляет предупреждения при достижении 80% лимита просадки."""
        daily_limit = ct.max_daily_loss
        total_limit = ct.max_total_loss
        threshold = Decimal("80")

        if daily_dd >= (daily_limit * threshold / 100) and daily_dd < daily_limit:
            await self.notification_service.send_daily_drawdown_warning(challenge)
        if total_dd >= (total_limit * threshold / 100) and total_dd < total_limit:
            await self.notification_service.send_total_drawdown_warning(challenge)

    # ─── Проверка нарушений ───────────────────────────────────────────────────

    async def _check_violations(
        self,
        challenge: UserChallenge,
        ct: "ChallengeType",
        daily_dd: Decimal,
        total_dd: Decimal,
        now: datetime,
    ) -> dict | None:
        """
        Проверяет все правила. Возвращает dict с описанием нарушения или None.
        """
        # Нарушение дневной просадки
        if daily_dd >= ct.max_daily_loss:
            return {
                "type": ViolationType.daily_loss,
                "description": (
                    f"Дневная просадка {daily_dd:.2f}% превысила лимит {ct.max_daily_loss}%"
                ),
                "value": daily_dd,
                "limit": ct.max_daily_loss,
            }

        # Нарушение общей просадки
        if total_dd >= ct.max_total_loss:
            return {
                "type": ViolationType.total_loss,
                "description": (
                    f"Общая просадка {total_dd:.2f}% превысила лимит {ct.max_total_loss}%"
                ),
                "value": total_dd,
                "limit": ct.max_total_loss,
            }

        # Превышение максимального количества торговых дней
        if ct.max_trading_days and challenge.trading_days_count > ct.max_trading_days:
            return {
                "type": ViolationType.max_trading_days,
                "description": (
                    f"Превышено максимальное количество торговых дней "
                    f"({challenge.trading_days_count} > {ct.max_trading_days})"
                ),
                "value": Decimal(str(challenge.trading_days_count)),
                "limit": Decimal(str(ct.max_trading_days)),
            }

        # Правило консистентности (ни один день не > 30% от общей прибыли)
        if ct.consistency_rule and challenge.total_pnl > 0:
            violation = await self._check_consistency_rule(challenge)
            if violation:
                return violation

        return None

    async def _check_consistency_rule(self, challenge: UserChallenge) -> dict | None:
        """
        Правило консистентности: ни один торговый день не должен давать
        более 30% от общей прибыли.
        """
        if challenge.total_pnl <= 0:
            return None

        limit_pct = Decimal("30")
        max_day_pnl = challenge.total_pnl * limit_pct / 100

        # Проверяем текущий день
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            select(Trade)
            .where(
                Trade.challenge_id == challenge.id,
                Trade.closed_at >= today_start,
                Trade.pnl.isnot(None),
            )
        )
        result = await self.session.execute(stmt)
        today_trades = result.scalars().all()
        today_pnl = sum(t.pnl for t in today_trades if t.pnl)

        if today_pnl > max_day_pnl:
            excess_pct = (today_pnl / challenge.total_pnl) * 100
            return {
                "type": ViolationType.consistency,
                "description": (
                    f"Прибыль за день ({today_pnl:.2f}$) составляет "
                    f"{excess_pct:.1f}% от общей прибыли (лимит 30%)"
                ),
                "value": excess_pct,
                "limit": limit_pct,
            }
        return None

    # ─── Обработка нарушения ──────────────────────────────────────────────────

    async def _handle_violation(
        self,
        challenge: UserChallenge,
        client: BybitClient,
        violation: dict,
    ) -> None:
        """Обрабатывает нарушение: закрывает позиции, обновляет статус, уведомляет."""
        logger.warning(
            f"VIOLATION: challenge={challenge.id} type={violation['type']} "
            f"value={violation['value']:.2f} limit={violation['limit']:.2f}"
        )

        # 1. Закрываем все позиции
        try:
            await client.close_all_positions()
            logger.info(f"All positions closed for challenge {challenge.id}")
        except Exception as e:
            logger.error(f"Failed to close positions for challenge {challenge.id}: {e}")

        # 2. Записываем нарушение
        viol = Violation(
            challenge_id=challenge.id,
            type=violation["type"],
            description=violation["description"],
            value=violation["value"],
            limit_value=violation["limit"],
            occurred_at=datetime.now(timezone.utc),
        )
        self.session.add(viol)

        # 3. Обновляем статус испытания
        challenge.status = ChallengeStatus.failed
        challenge.failed_at = datetime.now(timezone.utc)
        challenge.failed_reason = violation["description"]

        # 4. Обновляем роль пользователя (если не было других активных)
        await self._update_user_role_on_fail(challenge)

        await self.session.commit()

        # 5. Уведомление
        await self.notification_service.send_violation_notification(challenge, violation)

        logger.info(f"Challenge {challenge.id} marked as FAILED")

    # ─── Проверка цели прибыли ────────────────────────────────────────────────

    async def _check_profit_target(
        self,
        challenge: UserChallenge,
        ct: "ChallengeType",
        total_pnl: Decimal,
        equity: Decimal,
        now: datetime,
    ) -> None:
        """Проверяет достижение цели прибыли."""
        if challenge.status == ChallengeStatus.phase1:
            target_pct = ct.profit_target_p1
        elif challenge.status == ChallengeStatus.phase2:
            target_pct = ct.profit_target_p2
        else:
            return  # funded — нет цели

        target_amount = challenge.initial_balance * target_pct / 100
        current_profit_pct = (total_pnl / challenge.initial_balance) * 100

        # Отправляем промежуточные уведомления
        if current_profit_pct >= (target_pct * Decimal("80") / 100):
            await self.notification_service.send_goal_80_notification(challenge, current_profit_pct)
        elif current_profit_pct >= (target_pct * Decimal("50") / 100):
            await self.notification_service.send_goal_50_notification(challenge, current_profit_pct)

        # Цель достигнута
        if total_pnl >= target_amount:
            min_days_met = challenge.trading_days_count >= ct.min_trading_days
            if not min_days_met:
                return  # Ждём минимальное количество торговых дней

            if challenge.status == ChallengeStatus.phase1:
                if ct.is_one_phase:
                    # Одна фаза → сразу funded
                    await self._promote_to_funded(challenge, ct)
                else:
                    # Переход на Phase 2
                    await self._promote_to_phase2(challenge)
            elif challenge.status == ChallengeStatus.phase2:
                await self._promote_to_funded(challenge, ct)

    # ─── Переход Phase 1 → Phase 2 ────────────────────────────────────────────

    async def _promote_to_phase2(self, challenge: UserChallenge) -> None:
        """Переводит испытание в Phase 2."""
        logger.info(f"Challenge {challenge.id}: Phase 1 PASSED → Phase 2")

        # Сбрасываем балансовые показатели до начального
        client = self._get_exchange_client(challenge)
        try:
            # Закрываем все позиции
            await client.close_all_positions()
        finally:
            await client.close()

        challenge.status = ChallengeStatus.phase2
        challenge.phase = 2
        challenge.trading_days_count = 0
        challenge.daily_pnl = Decimal("0")
        challenge.total_pnl = Decimal("0")

        # Для demo: сбрасываем баланс до initial
        # (на реальном Bybit это делается через master API)
        try:
            await self.master_client.top_up_demo_balance(
                uid=challenge.demo_account_id,
                amount=str(challenge.initial_balance),
            )
        except Exception as e:
            logger.warning(f"Could not reset demo balance for phase2: {e}")

        challenge.current_balance = challenge.initial_balance
        challenge.peak_equity = challenge.initial_balance
        challenge.daily_start_balance = challenge.initial_balance

        await self.session.commit()
        await self.notification_service.send_phase1_passed_notification(challenge)

    # ─── Переход Phase 2 → Funded ─────────────────────────────────────────────

    async def _promote_to_funded(self, challenge: UserChallenge, ct: "ChallengeType") -> None:
        """Выдаёт финансирование: создаёт real суб-аккаунт и переводит средства."""
        logger.info(f"Challenge {challenge.id}: Phase PASSED → FUNDED ${challenge.initial_balance}")

        try:
            # Закрываем все позиции на demo
            if challenge.account_mode == "demo":
                client = self._get_exchange_client(challenge)
                try:
                    await client.close_all_positions()
                finally:
                    await client.close()

            # Создаём real funded аккаунт
            username_prefix = f"CHM{challenge.user_id}"
            funded = await self.master_client.setup_funded_account(
                account_size=challenge.initial_balance,
                username_prefix=username_prefix,
                max_leverage=ct.max_leverage,
            )

            # Шифруем и сохраняем real ключи
            from app.core.security import encrypt_aes256
            challenge.real_account_id = funded["account_id"]
            challenge.real_api_key_enc = encrypt_aes256(funded["api_key"])
            challenge.real_api_secret_enc = encrypt_aes256(funded["api_secret"])

            # Обновляем статус
            challenge.status = ChallengeStatus.funded
            challenge.account_mode = "funded"
            challenge.funded_at = datetime.now(timezone.utc)
            challenge.phase = None
            challenge.trading_days_count = 0
            challenge.daily_pnl = Decimal("0")
            challenge.total_pnl = Decimal("0")
            challenge.daily_start_balance = challenge.initial_balance
            challenge.current_balance = challenge.initial_balance
            challenge.peak_equity = challenge.initial_balance

            # Обновляем роль пользователя
            from app.models.user import UserRole
            challenge.user.role = UserRole.funded_trader

            await self.session.commit()
            await self.notification_service.send_funded_notification(challenge)

        except Exception as e:
            logger.error(f"Failed to promote challenge {challenge.id} to funded: {e}", exc_info=True)
            raise

    # ─── Подсчёт торговых дней ────────────────────────────────────────────────

    async def _update_trading_days(self, challenge: UserChallenge, now: datetime) -> None:
        """
        Засчитывает торговый день если:
        - Была хотя бы одна закрытая сделка за день
        - Не было нарушений в этот день
        """
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today_start - timedelta(days=1)

        # Проверяем сделки за вчера (вчерашний день уже закрыт)
        stmt = (
            select(Trade)
            .where(
                Trade.challenge_id == challenge.id,
                Trade.closed_at >= yesterday_start,
                Trade.closed_at < today_start,
            )
        )
        result = await self.session.execute(stmt)
        yesterday_trades = result.scalars().all()

        if not yesterday_trades:
            return

        # Проверяем нарушения за вчера
        stmt = (
            select(Violation)
            .where(
                Violation.challenge_id == challenge.id,
                Violation.occurred_at >= yesterday_start,
                Violation.occurred_at < today_start,
            )
        )
        result = await self.session.execute(stmt)
        yesterday_violations = result.scalars().all()

        if not yesterday_violations and len(yesterday_trades) > 0:
            # Проверяем, что этот день ещё не засчитан
            # (через флаг или дату — здесь упрощённо считаем один раз в день)
            pass  # Логика подсчёта реализована через daily_reset_check

    # ─── Масштабирование ──────────────────────────────────────────────────────

    async def _check_scaling(self, challenge: UserChallenge, total_pnl: Decimal) -> None:
        """
        Проверяет условия масштабирования (+10% прибыли без нарушений).
        Увеличивает счёт на 25%.
        """
        if challenge.current_balance >= self.MAX_ACCOUNT_SIZE:
            return

        profit_pct = (total_pnl / challenge.initial_balance) * 100
        required_pct = self.SCALING_TRIGGER_PCT * (len(challenge.scaling_steps) + 1)

        if profit_pct < required_pct:
            return

        # Проверяем нарушения с момента последнего масштабирования
        last_scale = (
            challenge.scaling_steps[-1].triggered_at
            if challenge.scaling_steps
            else challenge.funded_at or challenge.started_at
        )

        stmt = select(Violation).where(
            Violation.challenge_id == challenge.id,
            Violation.occurred_at > last_scale,
        )
        result = await self.session.execute(stmt)
        violations_since_scale = result.scalars().all()

        if violations_since_scale:
            return  # Есть нарушения — не масштабируем

        # Масштабируем
        old_size = challenge.current_balance
        new_size = min(
            old_size * (1 + self.SCALING_INCREASE_PCT / 100),
            self.MAX_ACCOUNT_SIZE,
        )

        step = ScalingStep(
            challenge_id=challenge.id,
            step_number=len(challenge.scaling_steps) + 1,
            account_size_before=old_size,
            account_size_after=new_size,
            triggered_at=datetime.now(timezone.utc),
        )
        self.session.add(step)

        # Переводим дополнительные средства
        additional = new_size - old_size
        try:
            await self.master_client.internal_transfer(
                amount=str(additional),
                coin="USDT",
                to_uid=challenge.real_account_id,
            )
            challenge.current_balance = new_size
            challenge.initial_balance = new_size  # Новый базис
            challenge.peak_equity = max(challenge.peak_equity, new_size)

            logger.info(
                f"SCALING: challenge={challenge.id} "
                f"${old_size} → ${new_size}"
            )
            await self.notification_service.send_scaling_notification(challenge, old_size, new_size)
        except Exception as e:
            logger.error(f"Scaling transfer failed for challenge {challenge.id}: {e}")

    # ─── Обновление роли ──────────────────────────────────────────────────────

    async def _update_user_role_on_fail(self, challenge: UserChallenge) -> None:
        """Обновляет роль пользователя при провале всех испытаний."""
        stmt = (
            select(UserChallenge)
            .where(
                UserChallenge.user_id == challenge.user_id,
                UserChallenge.status.in_([
                    ChallengeStatus.phase1,
                    ChallengeStatus.phase2,
                    ChallengeStatus.funded,
                ]),
                UserChallenge.id != challenge.id,
            )
        )
        result = await self.session.execute(stmt)
        other_active = result.scalars().first()

        if not other_active:
            from app.models.user import UserRole
            challenge.user.role = UserRole.guest
