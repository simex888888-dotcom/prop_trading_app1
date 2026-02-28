"""
ReferralService — управление реферальной программой и выплатами.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.referral import Referral
from app.models.user import User
from app.models.challenge import UserChallenge
from app.services.notification_service import NotificationService

# Комиссии реферальной программы
LEVEL1_PCT = Decimal("0.10")   # 10% от суммы испытания
LEVEL2_PCT = Decimal("0.03")   # 3% от суммы испытания
MIN_PAYOUT = Decimal("10.0")   # Минимальная сумма для выплаты


class ReferralService:
    """Обрабатывает реферальные вознаграждения и еженедельные выплаты."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notif = NotificationService(session)

    # ── Public API ───────────────────────────────────────────────────────────

    async def create_referral_records(
        self,
        new_user_id: int,
        referrer_id: int,
    ) -> None:
        """Создаёт записи реферальной связи при регистрации."""
        # Level 1 — прямой реферал
        ref1 = Referral(
            referrer_id=referrer_id,
            referred_user_id=new_user_id,
            level=1,
        )
        self.session.add(ref1)

        # Level 2 — найти реферера реферера
        ref_of_referrer_q = await self.session.execute(
            select(Referral).where(
                Referral.referred_user_id == referrer_id,
                Referral.level == 1,
            )
        )
        ref_of_referrer = ref_of_referrer_q.scalar_one_or_none()
        if ref_of_referrer:
            ref2 = Referral(
                referrer_id=ref_of_referrer.referrer_id,
                referred_user_id=new_user_id,
                level=2,
            )
            self.session.add(ref2)

        await self.session.flush()

    async def on_challenge_purchase(
        self,
        buyer_id: int,
        challenge_price: Decimal,
    ) -> None:
        """Начисляет реферальный бонус при покупке испытания."""
        refs_q = await self.session.execute(
            select(Referral).where(Referral.referred_user_id == buyer_id)
        )
        refs = refs_q.scalars().all()

        for ref in refs:
            pct = LEVEL1_PCT if ref.level == 1 else LEVEL2_PCT
            bonus = (challenge_price * pct).quantize(Decimal("0.01"))
            ref.bonus_amount = (ref.bonus_amount or Decimal(0)) + bonus

        if refs:
            await self.session.flush()

    async def process_weekly_payouts(self) -> None:
        """Обрабатывает еженедельные реферальные выплаты."""
        # Find referrers with unpaid bonuses >= MIN_PAYOUT
        result = await self.session.execute(
            select(
                Referral.referrer_id,
                func.sum(Referral.bonus_amount).label("total")
            )
            .where(Referral.paid == False, Referral.bonus_amount > 0)  # noqa: E712
            .group_by(Referral.referrer_id)
            .having(func.sum(Referral.bonus_amount) >= float(MIN_PAYOUT))
        )
        rows = result.all()

        for row in rows:
            referrer_id = row.referrer_id
            total = Decimal(str(row.total))
            try:
                await self._pay_referrer(referrer_id, total)
            except Exception as e:
                logger.error(f"Referral payout failed for user {referrer_id}: {e}")

        if rows:
            await self.session.commit()
            logger.info(f"Processed referral payouts for {len(rows)} users")

    async def get_referral_info(self, user_id: int) -> dict:
        """Возвращает информацию о реферальной программе пользователя."""
        user_q = await self.session.execute(select(User).where(User.id == user_id))
        user = user_q.scalar_one()

        # Count direct referrals (level 1)
        l1_q = await self.session.execute(
            select(func.count()).select_from(Referral).where(
                Referral.referrer_id == user_id, Referral.level == 1
            )
        )
        l1_count = l1_q.scalar_one() or 0

        # Count indirect referrals (level 2)
        l2_q = await self.session.execute(
            select(func.count()).select_from(Referral).where(
                Referral.referrer_id == user_id, Referral.level == 2
            )
        )
        l2_count = l2_q.scalar_one() or 0

        # Total earned (all time)
        earned_q = await self.session.execute(
            select(func.sum(Referral.bonus_amount)).where(
                Referral.referrer_id == user_id
            )
        )
        total_earned = float(earned_q.scalar_one() or 0)

        # Pending (unpaid)
        pending_q = await self.session.execute(
            select(func.sum(Referral.bonus_amount)).where(
                Referral.referrer_id == user_id,
                Referral.paid == False,  # noqa: E712
            )
        )
        pending = float(pending_q.scalar_one() or 0)

        referral_code = user.referral_code or ""
        bot_username = "chm_krypton_bot"  # configurable
        referral_link = f"https://t.me/{bot_username}?start={referral_code}"

        return {
            "referral_code": referral_code,
            "referral_link": referral_link,
            "total_referrals": l1_count + l2_count,
            "level1_count": l1_count,
            "level2_count": l2_count,
            "total_earned": total_earned,
            "pending_payout": pending,
        }

    async def get_earnings(self, user_id: int) -> list[dict]:
        """Возвращает список реферальных заработков."""
        result = await self.session.execute(
            select(Referral, User)
            .join(User, User.id == Referral.referred_user_id)
            .where(Referral.referrer_id == user_id)
            .order_by(Referral.created_at.desc())
            .limit(100)
        )
        rows = result.all()
        return [
            {
                "id": ref.id,
                "referred_username": user.username,
                "bonus_amount": float(ref.bonus_amount or 0),
                "level": ref.level,
                "paid": ref.paid,
                "paid_at": ref.paid_at.isoformat() if ref.paid_at else None,
                "created_at": ref.created_at.isoformat(),
            }
            for ref, user in rows
        ]

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _pay_referrer(self, referrer_id: int, amount: Decimal) -> None:
        """Помечает бонусы как выплаченные и уведомляет пользователя."""
        now = datetime.now(timezone.utc)

        # Mark all unpaid bonuses as paid
        refs_q = await self.session.execute(
            select(Referral).where(
                Referral.referrer_id == referrer_id,
                Referral.paid == False,  # noqa: E712
                Referral.bonus_amount > 0,
            )
        )
        refs = refs_q.scalars().all()
        for ref in refs:
            ref.paid = True
            ref.paid_at = now

        # Notify user
        user_q = await self.session.execute(select(User).where(User.id == referrer_id))
        user = user_q.scalar_one_or_none()
        if user and user.telegram_id:
            await self.notif.send_to_user(
                user.telegram_id,
                f"💰 <b>Реферальная выплата!</b>\n\n"
                f"Тебе начислено <b>{amount:.2f} USDT</b> за приглашённых трейдеров.\n"
                f"Средства добавлены к твоему балансу.",
            )
        logger.info(f"Paid {amount} USDT referral bonus to user {referrer_id}")
