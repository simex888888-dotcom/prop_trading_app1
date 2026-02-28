"""
LeaderboardService — построение и кеширование лидербордов.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_redis
from app.models.user import User
from app.models.challenge import UserChallenge, ChallengeStatus
from app.models.trade import Trade

MONTHLY_KEY = "leaderboard:monthly"
ALLTIME_KEY = "leaderboard:alltime"
CACHE_TTL = 300  # 5 minutes


class LeaderboardService:
    """Строит и кеширует рейтинги трейдеров."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Public API ───────────────────────────────────────────────────────────

    async def rebuild_cache(self) -> None:
        """Перестраивает оба лидерборда и сохраняет в Redis."""
        try:
            monthly = await self._build_monthly()
            alltime = await self._build_alltime()

            redis = await get_redis()
            await redis.setex(MONTHLY_KEY, CACHE_TTL, json.dumps(monthly))
            await redis.setex(ALLTIME_KEY, CACHE_TTL, json.dumps(alltime))
            logger.debug(f"Leaderboards rebuilt: monthly={len(monthly)}, alltime={len(alltime)}")
        except Exception as e:
            logger.error(f"Leaderboard rebuild failed: {e}")

    async def get_monthly(self, limit: int = 100) -> list[dict]:
        """Возвращает месячный лидерборд из кеша или базы."""
        redis = await get_redis()
        cached = await redis.get(MONTHLY_KEY)
        if cached:
            return json.loads(cached)[:limit]
        data = await self._build_monthly(limit)
        return data

    async def get_alltime(self, limit: int = 100) -> list[dict]:
        """Возвращает all-time лидерборд из кеша или базы."""
        redis = await get_redis()
        cached = await redis.get(ALLTIME_KEY)
        if cached:
            return json.loads(cached)[:limit]
        data = await self._build_alltime(limit)
        return data

    # ── Private builders ─────────────────────────────────────────────────────

    async def _build_monthly(self, limit: int = 100) -> list[dict]:
        """Строит месячный лидерборд: топ по % прибыли за текущий месяц."""
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Find challenges with funded or completed status, started this month or earlier
        result = await self.session.execute(
            select(UserChallenge, User)
            .join(User, User.id == UserChallenge.user_id)
            .where(
                UserChallenge.status.in_([ChallengeStatus.funded, ChallengeStatus.phase1, ChallengeStatus.phase2]),
                User.is_active == True,  # noqa: E712
            )
            .order_by(UserChallenge.total_pnl.desc())
            .limit(limit * 2)  # over-fetch for dedup
        )
        rows = result.all()

        # Aggregate by user (take best challenge per user)
        seen_users: set[int] = set()
        entries = []
        for challenge, user in rows:
            if user.id in seen_users:
                continue
            seen_users.add(user.id)

            total_pnl_pct = float(
                (challenge.total_pnl / challenge.initial_balance * 100)
                if challenge.initial_balance else Decimal(0)
            )

            # Count trades this month
            trade_count_q = await self.session.execute(
                select(func.count()).select_from(Trade).where(
                    Trade.user_id == user.id,
                    Trade.created_at >= month_start,
                )
            )
            trade_count = trade_count_q.scalar_one() or 0

            # Win rate this month
            win_q = await self.session.execute(
                select(func.count()).select_from(Trade).where(
                    Trade.user_id == user.id,
                    Trade.pnl > 0,
                    Trade.created_at >= month_start,
                )
            )
            wins = win_q.scalar_one() or 0
            win_rate = (wins / trade_count * 100) if trade_count > 0 else 0.0

            entries.append({
                "user_id": user.id,
                "username": user.username,
                "first_name": user.first_name or "",
                "avatar_url": user.avatar_url,
                "rank_name": self._get_rank_name(trade_count, win_rate),
                "total_pnl": float(challenge.total_pnl),
                "total_pnl_pct": total_pnl_pct,
                "account_size": float(challenge.initial_balance),
                "trading_days": challenge.trading_days_count,
                "win_rate": win_rate,
            })

            if len(entries) >= limit:
                break

        # Sort by % PnL descending
        entries.sort(key=lambda x: x["total_pnl_pct"], reverse=True)
        for i, e in enumerate(entries):
            e["rank"] = i + 1
        return entries

    async def _build_alltime(self, limit: int = 100) -> list[dict]:
        """Строит all-time лидерборд: топ по суммарной прибыли за всё время."""
        result = await self.session.execute(
            select(
                User.id,
                User.username,
                User.first_name,
                User.avatar_url,
                func.sum(UserChallenge.total_pnl).label("sum_pnl"),
                func.count(UserChallenge.id).label("challenge_count"),
            )
            .join(UserChallenge, UserChallenge.user_id == User.id)
            .where(User.is_active == True)  # noqa: E712
            .group_by(User.id, User.username, User.first_name, User.avatar_url)
            .order_by(func.sum(UserChallenge.total_pnl).desc())
            .limit(limit)
        )
        rows = result.all()

        entries = []
        for i, row in enumerate(rows):
            # Trade stats
            trade_count_q = await self.session.execute(
                select(func.count()).select_from(Trade).where(Trade.user_id == row.id)
            )
            trade_count = trade_count_q.scalar_one() or 0

            win_q = await self.session.execute(
                select(func.count()).select_from(Trade).where(
                    Trade.user_id == row.id, Trade.pnl > 0
                )
            )
            wins = win_q.scalar_one() or 0
            win_rate = (wins / trade_count * 100) if trade_count > 0 else 0.0

            entries.append({
                "rank": i + 1,
                "user_id": row.id,
                "username": row.username,
                "first_name": row.first_name or "",
                "avatar_url": row.avatar_url,
                "rank_name": self._get_rank_name(trade_count, win_rate),
                "total_pnl": float(row.sum_pnl or 0),
                "total_pnl_pct": 0.0,  # not meaningful for all-time
                "account_size": 0.0,
                "trading_days": trade_count,
                "win_rate": win_rate,
            })
        return entries

    @staticmethod
    def _get_rank_name(total_trades: int, win_rate: float) -> str:
        """Определяет ранг по количеству сделок и win rate."""
        if total_trades >= 500 and win_rate >= 75:
            return "Krypton"
        if total_trades >= 300 and win_rate >= 70:
            return "Nucleus"
        if total_trades >= 200 and win_rate >= 65:
            return "Crystal"
        if total_trades >= 100 and win_rate >= 60:
            return "Molecule"
        if total_trades >= 50 and win_rate >= 55:
            return "Catalyst"
        if total_trades >= 20:
            return "Reagent"
        return "Isotope"
