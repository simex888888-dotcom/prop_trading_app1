"""
Bybit Master Account Client — управление суб-аккаунтами, переводы, создание API ключей.
Используется только backend-сервисами, никогда трейдерами напрямую.

Три режима:
  mode="testnet" — работает с api-testnet.bybit.com (challenge фаза)
                   Testnet ПОДДЕРЖИВАЕТ создание суб-аккаунтов, трейдеры
                   видят настоящий Bybit интерфейс на testnet.bybit.com
  mode="demo"    — работает с api-demo.bybit.com (НЕ поддерживает суб-аккаунты,
                   оставлено для обратной совместимости)
  mode="real"    — работает с api.bybit.com (funded аккаунты, реальные деньги)
"""
import hashlib
import hmac
import json as json_lib
import time
from decimal import Decimal
from typing import Any, Literal, Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.services.exchange.bybit_client import BybitAPIError


class BybitMasterClient:
    """
    Master-аккаунт Bybit для управления суб-аккаунтами и переводами.

    mode="testnet" → api-testnet.bybit.com  (challenge phase — рекомендуется)
    mode="demo"    → api-demo.bybit.com     (НЕ поддерживает суб-аккаунты)
    mode="real"    → api.bybit.com          (funded phase, real USDT)
    """

    def __init__(self, mode: Literal["testnet", "demo", "real"] = "real"):
        self.mode = mode

        if mode == "testnet":
            self.api_key = settings.bybit_testnet_master_api_key
            self.api_secret = settings.bybit_testnet_master_api_secret
            if not self.api_key or not self.api_secret:
                raise ValueError(
                    "Bybit Testnet API ключи не настроены. "
                    "Задайте BYBIT_TESTNET_MASTER_API_KEY и BYBIT_TESTNET_MASTER_API_SECRET "
                    "в переменных окружения."
                )
            base_url = settings.bybit_testnet_base_url
        elif mode == "demo":
            self.api_key = settings.bybit_demo_master_api_key
            self.api_secret = settings.bybit_demo_master_api_secret
            if not self.api_key or not self.api_secret:
                raise ValueError(
                    "Bybit Demo API ключи не настроены. "
                    "Задайте BYBIT_DEMO_MASTER_API_KEY и BYBIT_DEMO_MASTER_API_SECRET "
                    "в переменных окружения."
                )
            base_url = settings.bybit_demo_base_url
        else:
            self.api_key = settings.bybit_master_api_key
            self.api_secret = settings.bybit_master_api_secret
            base_url = settings.bybit_real_base_url

        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=15.0,
            headers={"Content-Type": "application/json"},
        )

    # ─── Подпись ──────────────────────────────────────────────────────────────

    def _sign(self, timestamp: str, recv_window: str, payload: str) -> str:
        sign_str = f"{timestamp}{self.api_key}{recv_window}{payload}"
        return hmac.new(
            self.api_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _auth_headers(self, payload: str = "") -> dict[str, str]:
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        return {
            "X-BAPI-API-KEY": self.api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": self._sign(timestamp, recv_window, payload),
            "X-BAPI-RECV-WINDOW": recv_window,
        }

    # ─── HTTP методы ──────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        params = params or {}
        query_str = "&".join(f"{k}={v}" for k, v in sorted(params.items())) if params else ""
        headers = self._auth_headers(query_str)
        resp = await self._client.get(path, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        self._check(data)
        return data

    async def _post(self, path: str, body: dict | None = None) -> dict[str, Any]:
        body = body or {}
        body_str = json_lib.dumps(body, separators=(",", ":"))
        headers = self._auth_headers(body_str)
        resp = await self._client.post(path, content=body_str, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        self._check(data)
        return data

    def _check(self, data: dict) -> None:
        ret_code = data.get("retCode", 0)
        if ret_code != 0:
            raise BybitAPIError(ret_code, data.get("retMsg", ""), data)

    # ─── Баланс master кошелька ───────────────────────────────────────────────

    async def get_master_balance(self, coin: str = "USDT") -> Decimal:
        """Возвращает доступный баланс master аккаунта."""
        data = await self._get(
            "/v5/account/wallet-balance",
            {"accountType": "UNIFIED", "coin": coin}
        )
        result = data["result"]["list"]
        if not result:
            return Decimal("0")
        coins = {c["coin"]: c for c in result[0].get("coin", [])}
        usdt = coins.get(coin, {})
        return Decimal(str(usdt.get("availableToWithdraw", "0")))

    async def check_master_balance(self) -> bool:
        """Проверяет, что баланс master выше минимального порога."""
        balance = await self.get_master_balance()
        min_balance = Decimal(str(settings.bybit_master_min_balance))
        if balance < min_balance:
            logger.warning(f"Master balance {balance} USDT is below minimum {min_balance} USDT!")
            return False
        return True

    # ─── Суб-аккаунты ─────────────────────────────────────────────────────────

    async def create_sub_account(
        self,
        username: str,
        is_uta: bool = True,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Создаёт суб-аккаунт.

        mode="testnet" — работает на api-testnet.bybit.com ✓
        mode="real"    — работает на api.bybit.com ✓
        mode="demo"    — НЕ работает (ошибка 10032 от Bybit) ✗

        Returns: {"uid": str, "username": str, ...}
        """
        body: dict[str, Any] = {
            "username": username,
            "memberType": 1,  # 1 = normal sub-member
            "note": note or "CHM KRYPTON trader account",
        }
        if is_uta:
            body["accountType"] = "UNIFIED"

        data = await self._post("/v5/user/create-sub-member", body)
        uid = data["result"].get("uid")
        logger.info(f"[{self.mode}] Sub-account created: uid={uid}, username={username}")
        return data["result"]

    async def create_sub_api_key(
        self,
        sub_uid: str,
        permissions: Optional[dict] = None,
        note: str = "CHM KRYPTON Trading Key",
        read_only: bool = False,
    ) -> dict[str, Any]:
        """
        Создаёт API ключ для суб-аккаунта.
        Права: Trade + Position, НЕТ прав на вывод.
        Returns: {"id": str, "apiKey": str, "secret": str, ...}
        """
        if permissions is None:
            permissions = {
                "ContractTrade": ["Order", "Position"],
                "Wallet": ["AccountTransfer"],
            }

        body = {
            "subuid": int(sub_uid),
            "note": note,
            "readOnly": 0 if not read_only else 1,
            "permissions": permissions,
        }
        data = await self._post("/v5/user/create-sub-api", body)
        result = data["result"]
        logger.info(f"[{self.mode}] API key created for sub_uid={sub_uid}: key={result.get('apiKey', '')[:8]}...")
        return result

    # ─── Demo balance (только api-demo.bybit.com) ─────────────────────────────

    async def top_up_demo_balance_as_sub(
        self,
        sub_api_key: str,
        sub_api_secret: str,
        amount: str = "10000",
        coin: str = "USDT",
    ) -> dict[str, Any]:
        """
        Пополняет demo баланс суб-аккаунта через api-demo.bybit.com.

        ВАЖНО: Работает ТОЛЬКО на api-demo.bybit.com.
        На testnet/real используйте internal_transfer вместо этого метода.
        """
        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"
        body = {"adjustType": 0, "utaWalletBalance": amount, "coin": coin}
        body_str = json_lib.dumps(body, separators=(",", ":"))

        sign_str = f"{timestamp}{sub_api_key}{recv_window}{body_str}"
        signature = hmac.new(
            sub_api_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "X-BAPI-API-KEY": sub_api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(base_url=settings.bybit_demo_base_url, timeout=10.0) as client:
            resp = await client.post("/v5/account/demo-apply-money", content=body_str, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        if data.get("retCode", 0) != 0:
            raise BybitAPIError(data["retCode"], data.get("retMsg", ""), data)

        logger.info(f"Demo balance top-up: {amount} {coin} (via sub-account credentials)")
        return data.get("result", {})

    # ─── Переводы между аккаунтами ────────────────────────────────────────────

    async def internal_transfer(
        self,
        amount: str,
        coin: str = "USDT",
        from_account: str = "UNIFIED",
        to_account: str = "UNIFIED",
        to_uid: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Внутренний перевод средств на суб-аккаунт.
        Используется для testnet (challenge) и real (funded) режимов.
        """
        import uuid
        transfer_id = str(uuid.uuid4())
        body: dict[str, Any] = {
            "transferId": transfer_id,
            "coin": coin,
            "amount": amount,
            "fromAccountType": from_account,
            "toAccountType": to_account,
        }
        if to_uid:
            body["toMemberId"] = int(to_uid)

        endpoint = "/v5/asset/transfer/universal-transfer" if to_uid else "/v5/asset/transfer/inter-transfer"
        data = await self._post(endpoint, body)
        logger.info(f"Transfer {amount} {coin} to uid={to_uid}: transferId={transfer_id}")
        return data["result"]

    # ─── Ключи суб-аккаунта ───────────────────────────────────────────────────

    async def get_sub_api_keys(self, sub_uid: str) -> list[dict[str, Any]]:
        """Список API ключей суб-аккаунта."""
        data = await self._get("/v5/user/sub-apikeys", {"subuid": sub_uid})
        return data["result"].get("result", [])

    async def delete_sub_api_key(self, api_key: str) -> None:
        """Удаляет API ключ суб-аккаунта."""
        await self._post("/v5/user/delete-sub-api", {"apikey": api_key})
        logger.info(f"API key deleted: {api_key[:8]}...")

    # ─── Создание Testnet аккаунта для испытания (основной метод) ────────────

    async def setup_testnet_challenge_account(
        self,
        account_size: Decimal,
        username_prefix: str,
    ) -> dict[str, Any]:
        """
        Создаёт Testnet суб-аккаунт для испытания на api-testnet.bybit.com.

        Должен вызываться с mode="testnet".

        Шаги:
        1. Создаём testnet суб-аккаунт
        2. Переводим testnet USDT с master на суб-аккаунт
        3. Создаём API ключи для суб-аккаунта

        Трейдер получает API ключи и может торговать через:
        - Встроенный терминал приложения (подключается к api-testnet.bybit.com)
        - testnet.bybit.com (через управление суб-аккаунтами мастера)
        - Любой терминал совместимый с Bybit API

        Returns: {"account_id": str, "username": str, "api_key": str, "api_secret": str}
        """
        import secrets
        suffix = secrets.token_hex(4).upper()
        username = f"{username_prefix}_{suffix}"

        # 1. Создать testnet суб-аккаунт
        sub = await self.create_sub_account(username=username)
        sub_uid = str(sub["uid"])

        # 2. Перевести testnet USDT с master на суб-аккаунт
        await self.internal_transfer(
            amount=str(int(account_size)),
            coin="USDT",
            to_uid=sub_uid,
        )

        # 3. Создать API ключи для суб-аккаунта
        api_result = await self.create_sub_api_key(
            sub_uid=sub_uid,
            note=f"CHM KRYPTON Testnet Challenge {username}",
        )

        logger.info(
            f"Testnet challenge account ready: uid={sub_uid}, "
            f"username={username}, balance={account_size} USDT"
        )
        return {
            "account_id": sub_uid,
            "username": username,
            "api_key": api_result["apiKey"],
            "api_secret": api_result["secret"],
        }

    # ─── Создание Demo аккаунта (устаревший метод) ────────────────────────────

    async def setup_demo_challenge_account(
        self,
        account_size: Decimal,
        username_prefix: str,
    ) -> dict[str, Any]:
        """
        [УСТАРЕВШИЙ] Создаёт Demo суб-аккаунт через api-demo.bybit.com.

        ВНИМАНИЕ: Bybit Demo Trading (api-demo.bybit.com) не поддерживает
        создание суб-аккаунтов (ошибка retCode=10032).
        Используйте setup_testnet_challenge_account вместо этого.

        Этот метод оставлен для обратной совместимости.
        """
        import secrets
        suffix = secrets.token_hex(4).upper()
        username = f"{username_prefix}_{suffix}"

        sub = await self.create_sub_account(username=username)
        sub_uid = str(sub["uid"])

        api_result = await self.create_sub_api_key(
            sub_uid=sub_uid,
            note=f"CHM KRYPTON Demo Challenge {username}",
        )
        sub_api_key = api_result["apiKey"]
        sub_api_secret = api_result["secret"]

        await self.top_up_demo_balance_as_sub(
            sub_api_key=sub_api_key,
            sub_api_secret=sub_api_secret,
            amount=str(int(account_size)),
        )

        logger.info(
            f"Demo challenge account ready: uid={sub_uid}, "
            f"username={username}, balance={account_size} USDT"
        )
        return {
            "account_id": sub_uid,
            "username": username,
            "api_key": sub_api_key,
            "api_secret": sub_api_secret,
        }

    # ─── Создание Funded аккаунта ──────────────────────────────────────────────

    async def setup_funded_account(
        self,
        account_size: Decimal,
        username_prefix: str,
        max_leverage: int = 50,
    ) -> dict[str, Any]:
        """
        Создаёт реальный funded суб-аккаунт с переводом USDT.

        Должен вызываться с mode="real".

        Шаги:
        1. Проверяем баланс master
        2. Создаём real суб-аккаунт
        3. Переводим USDT с master
        4. Создаём API ключи (без прав на вывод)

        Returns: {"account_id": str, "username": str, "api_key": str, "api_secret": str}
        """
        import secrets
        suffix = secrets.token_hex(4).upper()
        username = f"{username_prefix}_F_{suffix}"

        # 1. Проверяем баланс master
        if not await self.check_master_balance():
            raise ValueError("Master balance is below minimum threshold")

        # 2. Создать real суб-аккаунт
        sub = await self.create_sub_account(
            username=username,
            note="CHM KRYPTON Funded Account",
        )
        sub_uid = str(sub["uid"])

        # 3. Перевести реальные средства
        await self.internal_transfer(
            amount=str(account_size),
            coin="USDT",
            to_uid=sub_uid,
        )

        # 4. Создать API ключи
        api_result = await self.create_sub_api_key(
            sub_uid=sub_uid,
            note=f"CHM KRYPTON Funded {username}",
        )

        logger.info(
            f"Funded account ready: uid={sub_uid}, "
            f"username={username}, balance={account_size} USDT"
        )
        return {
            "account_id": sub_uid,
            "username": username,
            "api_key": api_result["apiKey"],
            "api_secret": api_result["secret"],
        }

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
