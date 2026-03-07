"""
/paper — симуляционная торговля (paper trading).
Не требует Bybit аккаунта. Цены берутся из публичного API Bybit.
Начальный капитал: $10,000. Позиции хранятся в БД.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.paper_position import PaperPosition, PaperSide
from app.models.user import User
from app.schemas.common import APIResponse

router = APIRouter(prefix="/paper", tags=["paper"])

PAPER_INITIAL_BALANCE = Decimal("10000.00")
BYBIT_PUBLIC_URL = "https://api.bybit.com/v5/market/tickers"


# ─── Schemas ──────────────────────────────────────────────────────────────────

class PaperPositionOut(BaseModel):
    id: int
    symbol: str
    side: str
    qty: float
    entry_price: float
    leverage: int
    take_profit: Optional[float]
    stop_loss: Optional[float]
    exit_price: Optional[float]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    is_closed: bool
    margin_used: float
    opened_at: datetime
    closed_at: Optional[datetime]
    unrealized_pnl: Optional[float] = None

    model_config = {"from_attributes": True}


class PaperBalanceOut(BaseModel):
    balance: float
    equity: float
    unrealized_pnl: float
    margin_used: float
    available: float


class PlacePaperOrderRequest(BaseModel):
    symbol: str
    side: Literal["Buy", "Sell"]
    qty: str
    leverage: int = 1
    stop_loss: Optional[str] = None
    take_profit: Optional[str] = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_price(symbol: str) -> Decimal:
    """Берёт текущую цену из публичного Bybit API."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(
            BYBIT_PUBLIC_URL,
            params={"category": "linear", "symbol": symbol},
        )
    data = resp.json()
    items = data.get("result", {}).get("list", [])
    if not items:
        raise HTTPException(status_code=400, detail=f"Пара {symbol} не найдена")
    return Decimal(str(items[0]["lastPrice"]))


async def _compute_balance(user_id: int, session: AsyncSession) -> tuple[Decimal, Decimal, Decimal]:
    """Возвращает (realized_balance, unrealized_pnl, margin_used)."""
    result = await session.execute(
        select(PaperPosition).where(PaperPosition.user_id == user_id)
    )
    positions = result.scalars().all()

    # realized = initial + sum of closed pnl
    realized = PAPER_INITIAL_BALANCE
    for p in positions:
        if p.is_closed and p.pnl is not None:
            realized += p.pnl

    # For open positions fetch prices concurrently would be ideal but httpx is fine
    unrealized = Decimal("0")
    margin_used = Decimal("0")
    for p in positions:
        if not p.is_closed:
            margin_used += p.margin_used
            try:
                cur_price = await _get_price(p.symbol)
                if p.side == PaperSide.Buy:
                    upnl = (cur_price - p.entry_price) * p.qty * p.leverage
                else:
                    upnl = (p.entry_price - cur_price) * p.qty * p.leverage
                unrealized += upnl
            except Exception:
                pass

    return realized, unrealized, margin_used


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get("/balance", response_model=APIResponse[PaperBalanceOut])
async def get_paper_balance(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[PaperBalanceOut]:
    realized, unrealized, margin_used = await _compute_balance(user.id, session)
    equity = realized + unrealized
    available = realized - margin_used
    if available < 0:
        available = Decimal("0")
    return APIResponse(data=PaperBalanceOut(
        balance=float(realized),
        equity=float(equity),
        unrealized_pnl=float(unrealized),
        margin_used=float(margin_used),
        available=float(available),
    ))


@router.get("/positions", response_model=APIResponse[list[PaperPositionOut]])
async def get_paper_positions(
    closed: bool = Query(False),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[PaperPositionOut]]:
    result = await session.execute(
        select(PaperPosition).where(
            PaperPosition.user_id == user.id,
            PaperPosition.is_closed == closed,
        ).order_by(PaperPosition.opened_at.desc())
    )
    positions = result.scalars().all()

    out = []
    for p in positions:
        upnl = None
        if not p.is_closed:
            try:
                cur_price = await _get_price(p.symbol)
                if p.side == PaperSide.Buy:
                    upnl = float((cur_price - p.entry_price) * p.qty * p.leverage)
                else:
                    upnl = float((p.entry_price - cur_price) * p.qty * p.leverage)
            except Exception:
                pass

        out.append(PaperPositionOut(
            id=p.id,
            symbol=p.symbol,
            side=p.side,
            qty=float(p.qty),
            entry_price=float(p.entry_price),
            leverage=p.leverage,
            take_profit=float(p.take_profit) if p.take_profit else None,
            stop_loss=float(p.stop_loss) if p.stop_loss else None,
            exit_price=float(p.exit_price) if p.exit_price else None,
            pnl=float(p.pnl) if p.pnl is not None else None,
            pnl_pct=float(p.pnl_pct) if p.pnl_pct is not None else None,
            is_closed=p.is_closed,
            margin_used=float(p.margin_used),
            opened_at=p.opened_at,
            closed_at=p.closed_at,
            unrealized_pnl=upnl,
        ))

    return APIResponse(data=out)


@router.post("/order", response_model=APIResponse[PaperPositionOut])
async def place_paper_order(
    req: PlacePaperOrderRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[PaperPositionOut]:
    qty = Decimal(req.qty)
    if qty <= 0:
        raise HTTPException(status_code=400, detail="qty должен быть > 0")
    if req.leverage < 1 or req.leverage > 100:
        raise HTTPException(status_code=400, detail="leverage должен быть 1-100")

    price = await _get_price(req.symbol)
    margin = (price * qty) / req.leverage

    # Check available balance
    realized, _, margin_used = await _compute_balance(user.id, session)
    available = realized - margin_used
    if margin > available:
        raise HTTPException(status_code=400, detail=f"Недостаточно средств. Доступно: ${float(available):.2f}")

    now = datetime.now(timezone.utc)
    pos = PaperPosition(
        user_id=user.id,
        symbol=req.symbol,
        side=PaperSide(req.side),
        qty=qty,
        entry_price=price,
        leverage=req.leverage,
        take_profit=Decimal(req.take_profit) if req.take_profit else None,
        stop_loss=Decimal(req.stop_loss) if req.stop_loss else None,
        margin_used=margin,
        opened_at=now,
        created_at=now,
        updated_at=now,
    )
    session.add(pos)
    await session.commit()
    await session.refresh(pos)

    return APIResponse(data=PaperPositionOut(
        id=pos.id,
        symbol=pos.symbol,
        side=pos.side,
        qty=float(pos.qty),
        entry_price=float(pos.entry_price),
        leverage=pos.leverage,
        take_profit=float(pos.take_profit) if pos.take_profit else None,
        stop_loss=float(pos.stop_loss) if pos.stop_loss else None,
        exit_price=None,
        pnl=None,
        pnl_pct=None,
        is_closed=False,
        margin_used=float(pos.margin_used),
        opened_at=pos.opened_at,
        closed_at=None,
        unrealized_pnl=0.0,
    ))


@router.post("/close/{position_id}", response_model=APIResponse[PaperPositionOut])
async def close_paper_position(
    position_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[PaperPositionOut]:
    result = await session.execute(
        select(PaperPosition).where(
            PaperPosition.id == position_id,
            PaperPosition.user_id == user.id,
        )
    )
    pos = result.scalar_one_or_none()
    if not pos:
        raise HTTPException(status_code=404, detail="Позиция не найдена")
    if pos.is_closed:
        raise HTTPException(status_code=400, detail="Позиция уже закрыта")

    exit_price = await _get_price(pos.symbol)
    if pos.side == PaperSide.Buy:
        pnl = (exit_price - pos.entry_price) * pos.qty * pos.leverage
    else:
        pnl = (pos.entry_price - exit_price) * pos.qty * pos.leverage

    # pnl_pct relative to margin
    pnl_pct = (pnl / pos.margin_used * 100) if pos.margin_used > 0 else Decimal("0")

    now = datetime.now(timezone.utc)
    pos.exit_price = exit_price
    pos.pnl = pnl
    pos.pnl_pct = pnl_pct
    pos.is_closed = True
    pos.closed_at = now
    pos.updated_at = now

    await session.commit()
    await session.refresh(pos)

    return APIResponse(data=PaperPositionOut(
        id=pos.id,
        symbol=pos.symbol,
        side=pos.side,
        qty=float(pos.qty),
        entry_price=float(pos.entry_price),
        leverage=pos.leverage,
        take_profit=float(pos.take_profit) if pos.take_profit else None,
        stop_loss=float(pos.stop_loss) if pos.stop_loss else None,
        exit_price=float(pos.exit_price),
        pnl=float(pos.pnl),
        pnl_pct=float(pos.pnl_pct),
        is_closed=True,
        margin_used=float(pos.margin_used),
        opened_at=pos.opened_at,
        closed_at=pos.closed_at,
    ))


@router.delete("/reset", response_model=APIResponse[dict])
async def reset_paper_account(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Сброс paper аккаунта — удаляет все позиции, баланс возвращается к $10,000."""
    result = await session.execute(
        select(PaperPosition).where(PaperPosition.user_id == user.id)
    )
    for pos in result.scalars().all():
        await session.delete(pos)
    await session.commit()
    return APIResponse(data={"reset": True, "new_balance": float(PAPER_INITIAL_BALANCE)})
