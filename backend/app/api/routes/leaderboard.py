"""
/leaderboard — глобальные рейтинги трейдеров.
"""
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db, get_redis
from app.models.challenge import ChallengeStatus, UserChallenge
from app.models.user import User
from app.schemas.common import APIResponse

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    username: Optional[str]
    first_name: str
    avatar_url: Optional[str]
    total_pnl_pct: float
    total_pnl: float
    account_size: float
    trading_days: int


async def _build_leaderboard(
    session: AsyncSession,
    monthly: bool = True,
    limit: int = 100,
) -> list[LeaderboardEntry]:
    """Строит лидерборд из БД."""
    from app.models.challenge import DrawdownType

    stmt = (
        select(
            UserChallenge.user_id,
            User.username,
            User.first_name,
            User.avatar_url,
            UserChallenge.total_pnl,
            UserChallenge.initial_balance,
            UserChallenge.trading_days_count,
        )
        .join(User, UserChallenge.user_id == User.id)
        .where(
            UserChallenge.status.in_([
                ChallengeStatus.funded,
                ChallengeStatus.completed,
            ])
        )
    )

    if monthly:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stmt = stmt.where(UserChallenge.funded_at >= month_start)

    stmt = stmt.order_by(
        (UserChallenge.total_pnl / UserChallenge.initial_balance).desc()
    ).limit(limit)

    result = await session.execute(stmt)
    rows = result.all()

    entries = []
    for idx, row in enumerate(rows, start=1):
        pnl_pct = (float(row.total_pnl) / float(row.initial_balance) * 100) if row.initial_balance else 0
        entries.append(LeaderboardEntry(
            rank=idx,
            user_id=row.user_id,
            username=row.username,
            first_name=row.first_name,
            avatar_url=row.avatar_url,
            total_pnl_pct=round(pnl_pct, 2),
            total_pnl=round(float(row.total_pnl), 2),
            account_size=float(row.initial_balance),
            trading_days=row.trading_days_count,
        ))
    return entries


@router.get("/monthly", response_model=APIResponse[list[LeaderboardEntry]])
async def get_monthly_leaderboard(
    limit: int = Query(100, le=100),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[LeaderboardEntry]]:
    """Топ-100 за текущий месяц."""
    redis = await get_redis()
    cache_key = "leaderboard:monthly"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return APIResponse(data=[LeaderboardEntry(**d) for d in data[:limit]])

    entries = await _build_leaderboard(session, monthly=True, limit=100)
    await redis.setex(cache_key, 300, json.dumps([e.model_dump() for e in entries]))
    return APIResponse(data=entries[:limit])


@router.get("/alltime", response_model=APIResponse[list[LeaderboardEntry]])
async def get_alltime_leaderboard(
    limit: int = Query(100, le=100),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[LeaderboardEntry]]:
    """Топ-100 за всё время."""
    redis = await get_redis()
    cache_key = "leaderboard:alltime"
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return APIResponse(data=[LeaderboardEntry(**d) for d in data[:limit]])

    entries = await _build_leaderboard(session, monthly=False, limit=100)
    await redis.setex(cache_key, 300, json.dumps([e.model_dump() for e in entries]))
    return APIResponse(data=entries[:limit])
