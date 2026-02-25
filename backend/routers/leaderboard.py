import json
import logging
from decimal import Decimal
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, get_redis
from models import Account, AccountPhase, AccountStatus, User
from services.pnl_calculator import calculate_win_rate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])

LEADERBOARD_CACHE_KEY = "leaderboard:top20"
LEADERBOARD_CACHE_TTL = 60  # 1 минута


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: int
    display_name: str
    phase: str
    current_balance: str
    profit_pct: str
    win_rate: str
    total_trades: int
    trading_days_count: int


@router.get("/top", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()

    cached = await redis.get(LEADERBOARD_CACHE_KEY)
    if cached:
        data = json.loads(cached)
        return [LeaderboardEntry(**item) for item in data]

    result = await db.execute(
        select(Account, User)
        .join(User, Account.user_id == User.id)
        .where(
            and_(
                Account.status == AccountStatus.ACTIVE,
                Account.total_trades > 0,
            )
        )
        .order_by(
            (Account.current_balance - Account.initial_balance).desc()
        )
        .limit(20)
    )
    rows = result.all()

    entries = []
    for rank, (account, user) in enumerate(rows, start=1):
        initial = Decimal(str(account.initial_balance))
        current = Decimal(str(account.current_balance))
        profit_pct = Decimal("0")
        if initial > 0:
            profit_pct = ((current - initial) / initial * Decimal("100")).quantize(Decimal("0.01"))

        win_rate = calculate_win_rate(account.total_trades, account.winning_trades)

        display_name = user.username or user.first_name
        if len(display_name) > 20:
            display_name = display_name[:17] + "..."

        entries.append(LeaderboardEntry(
            rank=rank,
            user_id=user.id,
            display_name=display_name,
            phase=account.phase.value,
            current_balance=str(current.quantize(Decimal("0.01"))),
            profit_pct=str(profit_pct),
            win_rate=str(win_rate),
            total_trades=account.total_trades,
            trading_days_count=account.trading_days_count,
        ))

    serialized = [e.dict() for e in entries]
    await redis.setex(LEADERBOARD_CACHE_KEY, LEADERBOARD_CACHE_TTL, json.dumps(serialized))

    return entries
