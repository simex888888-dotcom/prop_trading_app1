"""
/trading — позиции, ордера, история сделок, баланс, WebSocket.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, rate_limit_standard, rate_limit_trading
from app.core.database import get_db
from app.core.security import decrypt_aes256
from app.models.challenge import ChallengeStatus, UserChallenge
from app.models.trade import Trade, TradeDirection
from app.models.user import User
from app.schemas.common import APIResponse, PaginatedResponse
from app.services.exchange.bybit_client import BybitAPIError, BybitClient

router = APIRouter(prefix="/trading", tags=["trading"])


# ─── Схемы ────────────────────────────────────────────────────────────────────

class BalanceOut(BaseModel):
    wallet_balance: float
    unrealized_pnl: float
    equity: float
    available_balance: float
    account_mode: str
    challenge_id: int


class PositionOut(BaseModel):
    symbol: str
    side: str
    size: float
    avg_price: float
    unrealized_pnl: float
    leverage: int
    take_profit: Optional[float]
    stop_loss: Optional[float]
    created_time: Optional[str]


class OrderOut(BaseModel):
    order_id: str
    symbol: str
    side: str
    order_type: str
    qty: float
    price: Optional[float]
    status: str
    created_time: str


class PlaceOrderRequest(BaseModel):
    symbol: str
    side: Literal["Buy", "Sell"]
    order_type: Literal["Market", "Limit"]
    qty: str
    price: Optional[str] = None
    stop_loss: Optional[str] = None
    take_profit: Optional[str] = None
    reduce_only: bool = False
    challenge_id: int


class CancelOrderRequest(BaseModel):
    challenge_id: int
    symbol: str


class TradeHistoryOut(BaseModel):
    id: int
    symbol: str
    direction: str
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    leverage: int
    pnl: Optional[float]
    pnl_pct: Optional[float]
    opened_at: datetime
    closed_at: Optional[datetime]
    duration_seconds: Optional[int]

    model_config = {"from_attributes": True}


class PairOut(BaseModel):
    symbol: str
    price: float
    change_24h_pct: float
    volume_24h: float
    high_24h: float
    low_24h: float


class KlineRequest(BaseModel):
    symbol: str
    interval: str = "60"
    limit: int = 200


# ─── Вспомогательные функции ──────────────────────────────────────────────────

async def _get_active_challenge(
    challenge_id: int, user: User, session: AsyncSession
) -> UserChallenge:
    """Получает активное испытание пользователя."""
    result = await session.execute(
        select(UserChallenge).where(
            UserChallenge.id == challenge_id,
            UserChallenge.user_id == user.id,
            UserChallenge.status.in_([
                ChallengeStatus.phase1,
                ChallengeStatus.phase2,
                ChallengeStatus.funded,
            ]),
        )
    )
    challenge = result.scalar_one_or_none()
    if not challenge:
        raise HTTPException(status_code=404, detail="Active challenge not found")
    return challenge


def _build_client(challenge: UserChallenge) -> BybitClient:
    """Создаёт Bybit клиент для испытания."""
    if challenge.account_mode == "demo":
        key = decrypt_aes256(challenge.demo_api_key_enc)
        secret = decrypt_aes256(challenge.demo_api_secret_enc)
        return BybitClient(api_key=key, api_secret=secret, mode="demo")
    else:
        key = decrypt_aes256(challenge.real_api_key_enc)
        secret = decrypt_aes256(challenge.real_api_secret_enc)
        return BybitClient(api_key=key, api_secret=secret, mode="real")


def _bybit_error_handler(func):
    """Декоратор для обработки ошибок Bybit API."""
    import functools
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BybitAPIError as e:
            raise HTTPException(status_code=400, detail=f"Exchange error: {e.ret_msg}")
    return wrapper


# ─── Баланс ───────────────────────────────────────────────────────────────────

@router.get("/balance", response_model=APIResponse[BalanceOut])
@_bybit_error_handler
async def get_balance(
    challenge_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[BalanceOut]:
    """Текущий баланс и equity."""
    challenge = await _get_active_challenge(challenge_id, user, session)
    client = _build_client(challenge)
    try:
        bal = await client.get_balance()
    finally:
        await client.close()

    return APIResponse(data=BalanceOut(
        wallet_balance=float(bal["wallet_balance"]),
        unrealized_pnl=float(bal["unrealized_pnl"]),
        equity=float(bal["equity"]),
        available_balance=float(bal["available_balance"]),
        account_mode=challenge.account_mode,
        challenge_id=challenge.id,
    ))


# ─── Позиции ──────────────────────────────────────────────────────────────────

@router.get("/positions", response_model=APIResponse[list[PositionOut]])
async def get_positions(
    challenge_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[PositionOut]]:
    """Список открытых позиций."""
    challenge = await _get_active_challenge(challenge_id, user, session)
    client = _build_client(challenge)
    try:
        positions = await client.get_positions()
    except BybitAPIError as e:
        raise HTTPException(status_code=400, detail=e.ret_msg)
    finally:
        await client.close()

    result = []
    for p in positions:
        size = float(p.get("size", 0))
        if size == 0:
            continue
        result.append(PositionOut(
            symbol=p["symbol"],
            side=p["side"],
            size=size,
            avg_price=float(p.get("avgPrice", 0)),
            unrealized_pnl=float(p.get("unrealisedPnl", 0)),
            leverage=int(float(p.get("leverage", 1))),
            take_profit=float(p["takeProfit"]) if p.get("takeProfit") else None,
            stop_loss=float(p["stopLoss"]) if p.get("stopLoss") else None,
            created_time=p.get("createdTime"),
        ))
    return APIResponse(data=result)


# ─── Ордера ───────────────────────────────────────────────────────────────────

@router.get("/orders", response_model=APIResponse[list[OrderOut]])
async def get_orders(
    challenge_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[OrderOut]]:
    """Список активных ордеров."""
    challenge = await _get_active_challenge(challenge_id, user, session)
    client = _build_client(challenge)
    try:
        orders = await client.get_open_orders()
    except BybitAPIError as e:
        raise HTTPException(status_code=400, detail=e.ret_msg)
    finally:
        await client.close()

    return APIResponse(data=[
        OrderOut(
            order_id=o["orderId"],
            symbol=o["symbol"],
            side=o["side"],
            order_type=o["orderType"],
            qty=float(o["qty"]),
            price=float(o["price"]) if o.get("price") and float(o["price"]) > 0 else None,
            status=o["orderStatus"],
            created_time=o.get("createdTime", ""),
        )
        for o in orders
    ])


@router.post("/order", response_model=APIResponse[dict])
async def place_order(
    body: PlaceOrderRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_trading),
) -> APIResponse[dict]:
    """Размещение ордера (рыночный/лимитный)."""
    challenge = await _get_active_challenge(body.challenge_id, user, session)
    client = _build_client(challenge)
    try:
        result = await client.place_order(
            symbol=body.symbol,
            side=body.side,
            order_type=body.order_type,
            qty=body.qty,
            price=body.price,
            stop_loss=body.stop_loss,
            take_profit=body.take_profit,
            reduce_only=body.reduce_only,
        )
    except BybitAPIError as e:
        raise HTTPException(status_code=400, detail=e.ret_msg)
    finally:
        await client.close()

    return APIResponse(data=result)


@router.delete("/order/{order_id}", response_model=APIResponse[dict])
async def cancel_order(
    order_id: str,
    body: CancelOrderRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_trading),
) -> APIResponse[dict]:
    """Отмена ордера."""
    challenge = await _get_active_challenge(body.challenge_id, user, session)
    client = _build_client(challenge)
    try:
        result = await client.cancel_order(symbol=body.symbol, order_id=order_id)
    except BybitAPIError as e:
        raise HTTPException(status_code=400, detail=e.ret_msg)
    finally:
        await client.close()
    return APIResponse(data=result)


@router.delete("/positions/all", response_model=APIResponse[list])
async def close_all_positions(
    challenge_id: int = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_trading),
) -> APIResponse[list]:
    """Закрытие всех открытых позиций."""
    challenge = await _get_active_challenge(challenge_id, user, session)
    client = _build_client(challenge)
    try:
        results = await client.close_all_positions()
    except BybitAPIError as e:
        raise HTTPException(status_code=400, detail=e.ret_msg)
    finally:
        await client.close()
    return APIResponse(data=results)


# ─── История сделок (cursor-based пагинация) ──────────────────────────────────

@router.get("/history", response_model=APIResponse[PaginatedResponse[TradeHistoryOut]])
async def get_trade_history(
    challenge_id: int = Query(...),
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    symbol: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[PaginatedResponse[TradeHistoryOut]]:
    """История закрытых сделок с cursor-based пагинацией."""
    challenge = await _get_active_challenge(challenge_id, user, session)
    _ = challenge  # проверка принадлежности

    stmt = (
        select(Trade)
        .where(Trade.challenge_id == challenge_id)
    )
    if symbol:
        stmt = stmt.where(Trade.symbol == symbol)
    if cursor:
        # cursor = trade.id
        stmt = stmt.where(Trade.id < int(cursor))
    stmt = stmt.order_by(Trade.id.desc()).limit(limit + 1)

    result = await session.execute(stmt)
    trades = result.scalars().all()
    has_more = len(trades) > limit
    trades = trades[:limit]
    next_cursor = str(trades[-1].id) if has_more and trades else None

    return APIResponse(data=PaginatedResponse(
        items=[TradeHistoryOut.model_validate(t) for t in trades],
        next_cursor=next_cursor,
        has_more=has_more,
    ))


# ─── Список пар ───────────────────────────────────────────────────────────────

@router.get("/pairs", response_model=APIResponse[list[PairOut]])
async def get_pairs(
    _: User = Depends(get_current_user),
) -> APIResponse[list[PairOut]]:
    """
    Список доступных торговых пар с ценами.
    Данные кешируются в Redis на 10 секунд.
    """
    import json
    from app.core.database import get_redis
    redis = await get_redis()
    cache_key = "pairs:linear:top50"
    cached = await redis.get(cache_key)
    if cached:
        return APIResponse(data=json.loads(cached))

    # Публичный запрос — не требует auth
    client = BybitClient(api_key="", api_secret="", mode="real")
    try:
        tickers = await client.get_tickers()
    finally:
        await client.close()

    # Фильтруем USDT перпетуалы, сортируем по объёму
    pairs = []
    for t in tickers:
        if not t["symbol"].endswith("USDT"):
            continue
        pairs.append(PairOut(
            symbol=t["symbol"],
            price=float(t.get("lastPrice", 0)),
            change_24h_pct=float(t.get("price24hPcnt", 0)) * 100,
            volume_24h=float(t.get("volume24h", 0)),
            high_24h=float(t.get("highPrice24h", 0)),
            low_24h=float(t.get("lowPrice24h", 0)),
        ))
    pairs.sort(key=lambda x: x.volume_24h, reverse=True)
    pairs = pairs[:50]

    await redis.setex(cache_key, 10, json.dumps([p.model_dump() for p in pairs]))
    return APIResponse(data=pairs)


# ─── Kline для графика ────────────────────────────────────────────────────────

@router.get("/kline", response_model=APIResponse[list])
async def get_kline(
    symbol: str = Query(...),
    interval: str = Query("60"),
    limit: int = Query(200, le=1000),
    _: User = Depends(get_current_user),
) -> APIResponse[list]:
    """OHLCV данные для TradingView lightweight-charts."""
    client = BybitClient(api_key="", api_secret="", mode="real")
    try:
        klines = await client.get_kline(symbol=symbol, interval=interval, limit=limit)
    except BybitAPIError as e:
        raise HTTPException(status_code=400, detail=e.ret_msg)
    finally:
        await client.close()

    # Конвертируем в формат TradingView: [time, open, high, low, close, volume]
    formatted = []
    for k in reversed(klines):  # Bybit возвращает в обратном порядке
        formatted.append({
            "time": int(k[0]) // 1000,
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })
    return APIResponse(data=formatted)


# ─── WebSocket для real-time данных ───────────────────────────────────────────

class ConnectionManager:
    """Менеджер WebSocket соединений."""
    def __init__(self):
        self.active: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self.active.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        if user_id in self.active:
            self.active[user_id].discard(ws) if hasattr(self.active[user_id], 'discard') else None
            try:
                self.active[user_id].remove(ws)
            except ValueError:
                pass

    async def broadcast_to_user(self, user_id: int, data: dict):
        import json
        connections = self.active.get(user_id, [])
        dead = []
        for ws in connections:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(user_id, ws)


ws_manager = ConnectionManager()


@router.websocket("/ws/{challenge_id}")
async def websocket_trading(
    websocket: WebSocket,
    challenge_id: int,
):
    """
    WebSocket для real-time обновлений: баланс, PnL, позиции.
    Обновление каждые 3 секунды.
    """
    import asyncio
    import json

    from app.core.security import decode_token

    # Аутентификация через query param
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    try:
        payload = decode_token(token)
        user_id = int(payload.get("sub", 0))
    except Exception:
        await websocket.close(code=4001, reason="Invalid token")
        return

    await ws_manager.connect(user_id, websocket)

    async for session in get_db():
        result = await session.execute(
            select(UserChallenge).where(
                UserChallenge.id == challenge_id,
                UserChallenge.user_id == user_id,
                UserChallenge.status.in_([
                    ChallengeStatus.phase1,
                    ChallengeStatus.phase2,
                    ChallengeStatus.funded,
                ]),
            )
        )
        challenge = result.scalar_one_or_none()
        break

    if not challenge:
        await websocket.close(code=4004, reason="Challenge not found")
        return

    client = _build_client(challenge)

    try:
        while True:
            try:
                # Получаем данные с биржи
                balance = await client.get_balance()
                positions = await client.get_positions()

                active_positions = [
                    {
                        "symbol": p["symbol"],
                        "side": p["side"],
                        "size": float(p.get("size", 0)),
                        "pnl": float(p.get("unrealisedPnl", 0)),
                        "avg_price": float(p.get("avgPrice", 0)),
                    }
                    for p in positions if float(p.get("size", 0)) > 0
                ]

                await websocket.send_json({
                    "type": "balance_update",
                    "data": {
                        "equity": float(balance["equity"]),
                        "wallet_balance": float(balance["wallet_balance"]),
                        "unrealized_pnl": float(balance["unrealized_pnl"]),
                        "positions": active_positions,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                })

                await asyncio.sleep(3)

            except WebSocketDisconnect:
                break
            except Exception as e:
                try:
                    await websocket.send_json({"type": "error", "message": str(e)})
                except Exception:
                    break
                await asyncio.sleep(5)
    finally:
        ws_manager.disconnect(user_id, websocket)
        await client.close()
