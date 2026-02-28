"""
AchievementService — проверка и выдача достижений пользователям.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.achievement import Achievement, UserAchievement
from app.models.trade import Trade
from app.models.challenge import UserChallenge, ChallengeStatus
from app.models.user import User
from app.models.referral import Referral
from app.services.notification_service import NotificationService


class AchievementService:
    """Проверяет условия для достижений и выдаёт их пользователям."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.notif = NotificationService(session)

    # ── Public API ───────────────────────────────────────────────────────────

    async def check_all_users(self) -> None:
        """Проверяет достижения для всех активных пользователей."""
        result = await self.session.execute(select(User).where(User.is_active == True))  # noqa: E712
        users = result.scalars().all()
        for user in users:
            try:
                await self.check_user(user.id)
            except Exception as e:
                logger.error(f"Achievement check failed for user {user.id}: {e}")

    async def check_user(self, user_id: int) -> list[str]:
        """Проверяет и выдаёт достижения конкретному пользователю.

        Returns список ключей новых достижений.
        """
        # Load all achievements
        ach_result = await self.session.execute(select(Achievement))
        all_achievements = ach_result.scalars().all()

        # Load already unlocked achievement IDs
        unlocked_result = await self.session.execute(
            select(UserAchievement.achievement_id).where(
                UserAchievement.user_id == user_id
            )
        )
        unlocked_ids = {row[0] for row in unlocked_result.all()}

        # Gather user stats
        stats = await self._get_user_stats(user_id)

        newly_unlocked = []
        for ach in all_achievements:
            if ach.id in unlocked_ids:
                continue
            if await self._check_achievement(ach, stats, user_id):
                await self._grant(user_id, ach)
                newly_unlocked.append(ach.key)

        if newly_unlocked:
            await self.session.commit()
            for key in newly_unlocked:
                await self._notify_achievement(user_id, key)

        return newly_unlocked

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _get_user_stats(self, user_id: int) -> dict[str, Any]:
        """Собирает статистику пользователя для проверки достижений."""
        # Total trades
        total_q = await self.session.execute(
            select(func.count()).select_from(Trade).where(
                Trade.user_id == user_id,
                Trade.closed_at.is_not(None),
            )
        )
        total_trades = total_q.scalar_one() or 0

        # Win / loss
        win_q = await self.session.execute(
            select(func.count()).select_from(Trade).where(
                Trade.user_id == user_id,
                Trade.pnl > 0,
                Trade.closed_at.is_not(None),
            )
        )
        wins = win_q.scalar_one() or 0
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0

        # Best single trade PnL
        best_q = await self.session.execute(
            select(func.max(Trade.pnl)).where(Trade.user_id == user_id)
        )
        best_pnl = best_q.scalar_one() or 0.0

        # Funded challenges
        funded_q = await self.session.execute(
            select(func.count()).select_from(UserChallenge).where(
                UserChallenge.user_id == user_id,
                UserChallenge.status == ChallengeStatus.funded,
            )
        )
        funded_count = funded_q.scalar_one() or 0

        # Referrals
        ref_q = await self.session.execute(
            select(func.count()).select_from(Referral).where(
                Referral.referrer_id == user_id,
                Referral.level == 1,
            )
        )
        referral_count = ref_q.scalar_one() or 0

        # Max consecutive wins (streak)
        trades_result = await self.session.execute(
            select(Trade.pnl)
            .where(Trade.user_id == user_id, Trade.closed_at.is_not(None))
            .order_by(Trade.closed_at)
        )
        pnls = [row[0] for row in trades_result.all()]
        max_streak = self._calc_streak(pnls)

        # Fast trade (< 5 min)
        fast_q = await self.session.execute(
            select(func.count()).select_from(Trade).where(
                Trade.user_id == user_id,
                Trade.pnl > 0,
                Trade.duration_seconds < 300,
                Trade.closed_at.is_not(None),
            )
        )
        fast_wins = fast_q.scalar_one() or 0

        # Night trades (22:00 – 06:00 UTC)
        all_trades_q = await self.session.execute(
            select(Trade.closed_at, Trade.pnl).where(
                Trade.user_id == user_id,
                Trade.closed_at.is_not(None),
            )
        )
        night_wins = sum(
            1 for closed_at, pnl in all_trades_q.all()
            if pnl > 0 and closed_at and (closed_at.hour >= 22 or closed_at.hour < 6)
        )

        # Symbols traded
        sym_q = await self.session.execute(
            select(func.count(Trade.symbol.distinct())).where(
                Trade.user_id == user_id
            )
        )
        symbols_count = sym_q.scalar_one() or 0

        # Completed challenges
        completed_q = await self.session.execute(
            select(func.count()).select_from(UserChallenge).where(
                UserChallenge.user_id == user_id,
                UserChallenge.status.in_([ChallengeStatus.funded, ChallengeStatus.completed]),
            )
        )
        completed_challenges = completed_q.scalar_one() or 0

        return {
            "total_trades": total_trades,
            "wins": wins,
            "win_rate": win_rate,
            "best_pnl": float(best_pnl),
            "funded_count": funded_count,
            "referral_count": referral_count,
            "max_streak": max_streak,
            "fast_wins": fast_wins,
            "night_wins": night_wins,
            "symbols_count": symbols_count,
            "completed_challenges": completed_challenges,
        }

    def _calc_streak(self, pnls: list) -> int:
        """Вычисляет максимальную серию подряд выигрышных сделок."""
        max_streak = 0
        current = 0
        for pnl in pnls:
            if float(pnl) > 0:
                current += 1
                max_streak = max(max_streak, current)
            else:
                current = 0
        return max_streak

    async def _check_achievement(self, ach: Achievement, stats: dict, user_id: int) -> bool:
        """Возвращает True если пользователь выполнил условие достижения."""
        k = ach.key
        t = stats["total_trades"]
        wr = stats["win_rate"]

        conditions: dict[str, bool] = {
            "first_blood": t >= 1,
            "sniper": wr >= 80 and t >= 20,
            "diamond_hands": stats["best_pnl"] >= 1000,
            "rocketeer": stats["funded_count"] >= 1,
            "guardian": stats["wins"] >= 50,
            "strategist": t >= 100,
            "scalper": t >= 50 and stats["fast_wins"] >= 10,
            "night_wolf": stats["night_wins"] >= 20,
            "legend": t >= 500 and wr >= 70,
            "streak_master": stats["max_streak"] >= 10,
            "consistent": wr >= 60 and t >= 30,
            "diversified": stats["symbols_count"] >= 5,
            "funded_elite": stats["funded_count"] >= 1,
            "scaled": False,  # handled separately by challenge engine
            "referral_master": stats["referral_count"] >= 10,
            "risk_manager": wr >= 65 and t >= 50,
            "swift_trader": stats["fast_wins"] >= 5,
            "bull_bear": False,  # requires both long and short
            "iron_discipline": False,  # no violations — complex
            "krypton_rank": stats["completed_challenges"] >= 3 and wr >= 75,
        }

        return conditions.get(k, False)

    async def _grant(self, user_id: int, ach: Achievement) -> None:
        """Записывает достижение пользователю."""
        ua = UserAchievement(
            user_id=user_id,
            achievement_id=ach.id,
            unlocked_at=datetime.now(timezone.utc),
            level="gold",
            progress=100,
        )
        self.session.add(ua)
        logger.info(f"Achievement '{ach.key}' granted to user {user_id}")

    async def _notify_achievement(self, user_id: int, key: str) -> None:
        """Уведомляет пользователя о новом достижении."""
        try:
            user_result = await self.session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_result.scalar_one_or_none()
            if user and user.telegram_id:
                await self.notif.send_to_user(
                    user.telegram_id,
                    f"🏆 <b>Новое достижение!</b>\n\nТы получил достижение <b>{key}</b>!\n"
                    f"Открой приложение, чтобы увидеть его.",
                )
        except Exception as e:
            logger.error(f"Failed to notify achievement: {e}")
