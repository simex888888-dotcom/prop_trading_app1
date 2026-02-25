import asyncio
import json
import logging
from decimal import Decimal
from typing import Dict, Optional

import httpx
import websockets

from database import get_redis

logger = logging.getLogger(__name__)

SUPPORTED_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "TONUSDT"]
BINANCE_REST_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_WS_URL = "wss://stream.binance.com:9443/stream"
PRICE_CACHE_TTL = 10  # seconds


async def fetch_price_rest(symbol: str) -> Decimal:
    """Получить текущую цену через Binance REST API."""
    redis = await get_redis()
    cache_key = f"price:{symbol}"

    cached = await redis.get(cache_key)
    if cached:
        return Decimal(cached)

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(BINANCE_REST_URL, params={"symbol": symbol})
        response.raise_for_status()
        data = response.json()
        price = Decimal(str(data["price"]))

    await redis.setex(cache_key, PRICE_CACHE_TTL, str(price))
    return price


async def fetch_all_prices() -> Dict[str, Decimal]:
    """Получить цены всех поддерживаемых символов одним запросом."""
    redis = await get_redis()

    # Пробуем взять всё из кэша
    prices = {}
    missing = []
    for sym in SUPPORTED_SYMBOLS:
        val = await redis.get(f"price:{sym}")
        if val:
            prices[sym] = Decimal(val)
        else:
            missing.append(sym)

    if not missing:
        return prices

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            "https://api.binance.com/api/v3/ticker/price",
        )
        response.raise_for_status()
        all_data = response.json()

    symbol_map = {item["symbol"]: item["price"] for item in all_data}
    pipe = redis.pipeline()
    for sym in missing:
        if sym in symbol_map:
            price = Decimal(str(symbol_map[sym]))
            prices[sym] = price
            pipe.setex(f"price:{sym}", PRICE_CACHE_TTL, str(price))
    await pipe.execute()

    return prices


class PriceFeedManager:
    """Менеджер WebSocket соединений для получения real-time цен с Binance."""

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run_websocket())
        logger.info("PriceFeedManager started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("PriceFeedManager stopped")

    async def _run_websocket(self):
        streams = "/".join([f"{sym.lower()}@aggTrade" for sym in SUPPORTED_SYMBOLS])
        ws_url = f"{BINANCE_WS_URL}?streams={streams}"
        redis = await get_redis()

        while self._running:
            try:
                async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                    logger.info("Connected to Binance WebSocket")
                    async for raw_message in ws:
                        if not self._running:
                            break
                        try:
                            envelope = json.loads(raw_message)
                            data = envelope.get("data", {})
                            symbol = data.get("s")
                            price_str = data.get("p")
                            if symbol and price_str and symbol in SUPPORTED_SYMBOLS:
                                price = Decimal(str(price_str))
                                await redis.setex(f"price:{symbol}", PRICE_CACHE_TTL, str(price))
                        except (json.JSONDecodeError, KeyError, Exception) as e:
                            logger.debug(f"WS message parse error: {e}")
            except Exception as e:
                logger.warning(f"WebSocket disconnected: {e}. Reconnecting in 3s...")
                await asyncio.sleep(3)


price_feed_manager = PriceFeedManager()
