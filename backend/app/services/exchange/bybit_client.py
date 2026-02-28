"""
Bybit Unified API v5 Client — Demo и Real режимы.
Документация: https://bybit-exchange.github.io/docs/v5/intro
"""
import hashlib
import hmac
import time
from decimal import Decimal
from typing import Any, Literal, Optional

import httpx
from loguru import logger

from app.core.config import settings


class BybitAPIError(Exception):
    def __init__(self, ret_code: int, ret_msg: str, raw: dict):
        self.ret_code = ret_code
        self.ret_msg = ret_msg
        self.raw = raw
        super().__init__(f"Bybit API error {ret_code}: {ret_msg}")


class BybitClient:
    """
    Клиент Bybit API v5 для demo и real аккаунтов трейдеров.
    Только perpetual futures (категория = linear).
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        mode: Literal["demo", "real"] = "demo",
        timeout: float = 10.0,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.mode = mode
        self.base_url = (
            settings.bybit_demo_base_url if mode == "demo"
            else settings.bybit_real_base_url
        )
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )

    # ─── Подпись запроса ──────────────────────────────────────────────────────

    def _sign(self, timestamp: str, recv_window: str, payload: str) -> str:
        """Генерирует HMAC-SHA256 подпись для Bybit API v5."""
        sign_str = f"{timestamp}{self.api_key}{recv_window}{payload}"
        return hmac.new(
            self.api_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _auth_headers(self, payload: str = "") -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        signature = self._sign(timestamp, recv_window, payload)
        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": recv_window,
        }

    # ─── Базовые методы запросов ──────────────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        params = params or {}
        query_str = "&".join(f"{k}={v}" for k, v in sorted(params.items())) if params else ""
        headers = self._auth_headers(query_str)
        try:
            resp = await self._client.get(path, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Bybit GET {path} HTTP error: {e}")
            raise
        self._check_response(data)
        return data

    async def _post(self, path: str, body: dict | None = None) -> dict[str, Any]:
        import json as json_lib
        body = body or {}
        body_str = json_lib.dumps(body, separators=(",", ":"))
        headers = self._auth_headers(body_str)
        try:
            resp = await self._client.post(path, content=body_str, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            logger.error(f"Bybit POST {path} HTTP error: {e}")
            raise
        self._check_response(data)
        return data

    def _check_response(self, data: dict) -> None:
        ret_code = data.get("retCode", 0)
        if ret_code != 0:
            raise BybitAPIError(ret_code, data.get("retMsg", "Unknown"), data)

    # ─── Баланс ───────────────────────────────────────────────────────────────

    async def get_balance(self, coin: str = "USDT") -> dict[str, Decimal]:
        """
        Возвращает баланс кошелька.
        Returns: {"wallet_balance": Decimal, "unrealized_pnl": Decimal, "equity": Decimal}
        """
        data = await self._get("/v5/account/wallet-balance", {"accountType": "UNIFIED", "coin": coin})
        result = data["result"]["list"]
        if not result:
            return {"wallet_balance": Decimal("0"), "unrealized_pnl": Decimal("0"), "equity": Decimal("0")}

        account = result[0]
        coins = {c["coin"]: c for c in account.get("coin", [])}
        usdt = coins.get(coin, {})
        return {
            "wallet_balance": Decimal(str(usdt.get("walletBalance", "0"))),
            "unrealized_pnl": Decimal(str(usdt.get("unrealisedPnl", "0"))),
            "equity": Decimal(str(usdt.get("equity", "0"))),
            "available_balance": Decimal(str(usdt.get("availableToWithdraw", "0"))),
        }

    # ─── Позиции ──────────────────────────────────────────────────────────────

    async def get_positions(self, symbol: Optional[str] = None) -> list[dict[str, Any]]:
        """Список открытых позиций (perpetual futures = linear category)."""
        params: dict[str, Any] = {"category": "linear", "settleCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol
        data = await self._get("/v5/position/list", params)
        return data["result"].get("list", [])

    # ─── Ордера ───────────────────────────────────────────────────────────────

    async def get_open_orders(self, symbol: Optional[str] = None) -> list[dict[str, Any]]:
        """Список активных ордеров."""
        params: dict[str, Any] = {"category": "linear", "settleCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol
        data = await self._get("/v5/order/realtime", params)
        return data["result"].get("list", [])

    async def place_order(
        self,
        symbol: str,
        side: Literal["Buy", "Sell"],
        order_type: Literal["Market", "Limit"],
        qty: str,
        price: Optional[str] = None,
        stop_loss: Optional[str] = None,
        take_profit: Optional[str] = None,
        reduce_only: bool = False,
        time_in_force: str = "GTC",
        position_idx: int = 0,
    ) -> dict[str, Any]:
        """
        Размещает ордер на бессрочные фьючерсы.
        position_idx: 0 = one-way, 1 = buy hedge, 2 = sell hedge
        """
        body: dict[str, Any] = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "timeInForce": time_in_force,
            "positionIdx": position_idx,
            "reduceOnly": reduce_only,
        }
        if order_type == "Limit" and price:
            body["price"] = price
        if stop_loss:
            body["stopLoss"] = stop_loss
        if take_profit:
            body["takeProfit"] = take_profit

        data = await self._post("/v5/order/create", body)
        logger.info(f"Order placed: {symbol} {side} {qty} @ {price or 'market'}")
        return data["result"]

    async def cancel_order(self, symbol: str, order_id: str) -> dict[str, Any]:
        """Отмена активного ордера."""
        body = {"category": "linear", "symbol": symbol, "orderId": order_id}
        data = await self._post("/v5/order/cancel", body)
        return data["result"]

    async def close_all_positions(self) -> list[dict[str, Any]]:
        """Закрывает все открытые позиции по рыночной цене."""
        positions = await self.get_positions()
        results = []
        for pos in positions:
            size = Decimal(str(pos.get("size", "0")))
            if size <= 0:
                continue
            symbol = pos["symbol"]
            side = pos["side"]  # "Buy" or "Sell"
            close_side: Literal["Buy", "Sell"] = "Sell" if side == "Buy" else "Buy"
            try:
                result = await self.place_order(
                    symbol=symbol,
                    side=close_side,
                    order_type="Market",
                    qty=str(size),
                    reduce_only=True,
                )
                results.append(result)
                logger.info(f"Closed position: {symbol} {side} size={size}")
            except BybitAPIError as e:
                logger.error(f"Failed to close {symbol}: {e}")
        return results

    # ─── История сделок ───────────────────────────────────────────────────────

    async def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> dict[str, Any]:
        """
        Получает историю закрытых сделок (cursor-based пагинация).
        Returns: {"list": [...], "nextPageCursor": str}
        """
        params: dict[str, Any] = {
            "category": "linear",
            "limit": limit,
        }
        if symbol:
            params["symbol"] = symbol
        if cursor:
            params["cursor"] = cursor
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        data = await self._get("/v5/execution/list", params)
        return data["result"]

    # ─── P&L истории (закрытые позиции) ──────────────────────────────────────

    async def get_closed_pnl(
        self,
        symbol: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None,
    ) -> dict[str, Any]:
        """Список закрытых P&L записей."""
        params: dict[str, Any] = {
            "category": "linear",
            "limit": limit,
        }
        if symbol:
            params["symbol"] = symbol
        if cursor:
            params["cursor"] = cursor

        data = await self._get("/v5/position/closed-pnl", params)
        return data["result"]

    # ─── Рыночные данные (публичные) ──────────────────────────────────────────

    async def get_tickers(self, symbol: Optional[str] = None) -> list[dict[str, Any]]:
        """Тикеры фьючерсных пар."""
        params: dict[str, Any] = {"category": "linear"}
        if symbol:
            params["symbol"] = symbol
        data = await self._get("/v5/market/tickers", params)
        return data["result"].get("list", [])

    async def get_kline(
        self,
        symbol: str,
        interval: str = "60",
        limit: int = 200,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> list[list]:
        """
        OHLCV данные для графика.
        interval: 1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M
        """
        params: dict[str, Any] = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        data = await self._get("/v5/market/kline", params)
        return data["result"].get("list", [])

    async def get_instruments(self, limit: int = 200) -> list[dict[str, Any]]:
        """Список всех доступных торговых пар (perpetual)."""
        params = {"category": "linear", "limit": limit, "status": "Trading"}
        data = await self._get("/v5/market/instruments-info", params)
        return data["result"].get("list", [])

    # ─── Настройка плеча ──────────────────────────────────────────────────────

    async def set_leverage(self, symbol: str, leverage: int) -> dict[str, Any]:
        """Устанавливает плечо для пары."""
        body = {
            "category": "linear",
            "symbol": symbol,
            "buyLeverage": str(leverage),
            "sellLeverage": str(leverage),
        }
        data = await self._post("/v5/position/set-leverage", body)
        return data.get("result", {})

    # ─── Cleanup ──────────────────────────────────────────────────────────────

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
