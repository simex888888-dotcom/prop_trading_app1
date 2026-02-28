"""
Bybit Master Account Client — управление суб-аккаунтами, переводы, создание API ключей.
Используется только backend-сервисами, никогда трейдерами.
"""
import hashlib
import hmac
import json as json_lib
import time
from decimal import Decimal
from typing import Any, Optional

import httpx
from loguru import logger

from app.core.config import settings
from app.services.exchange.bybit_client import BybitAPIError


class BybitMasterClient:
    """
    Master-аккаунт Bybit для управления суб-аккаунтами и переводами.

    Возможности:
    - Создание demo-участников (Demo Trading)
    - Создание real суб-аккаунтов
    - Создание API-ключей (без права вывода)
    - Переводы между master и суб-аккаунтами
    - Мониторинг баланса master кошелька
    """

    def __init__(self):
        self.api_key = settings.bybit_master_api_key
        self.api_secret = settings.bybit_master_api_secret
        self._client = httpx.AsyncClient(
            base_url=settings.bybit_real_base_url,
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
            logger.warning(
                f"Master balance {balance} USDT is below minimum {min_balance} USDT!"
            )
            return False
        return True

    # ─── Суб-аккаунты ─────────────────────────────────────────────────────────

    async def create_sub_account(
        self,
        username: str,
        password: Optional[str] = None,
        is_uta: bool = True,
        note: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Создаёт реальный суб-аккаунт.
        Returns: {"uid": str, "username": str, ...}
        """
        import secrets
        import string
        if password is None:
            alphabet = string.ascii_letters + string.digits + "!@#$"
            password = "".join(secrets.choice(alphabet) for _ in range(16))

        body: dict[str, Any] = {
            "username": username,
            "memberType": 1,  # 1 = normal sub-member
            "note": note or f"CHM_KRYPTON trader account",
        }
        if is_uta:
            body["accountType"] = "UNIFIED"

        data = await self._post("/v5/user/create-sub-member", body)
        logger.info(f"Sub-account created: uid={data['result'].get('uid')}")
        return data["result"]

    async def create_sub_api_key(
        self,
        sub_uid: str,
        permissions: Optional[dict] = None,
        note: str = "CHM_KRYPTON Trading Key",
        read_only: bool = False,
    ) -> dict[str, Any]:
        """
        Создаёт API ключ для суб-аккаунта.
        Права: Trade + Position, НЕТ прав на вывод (Withdrawal всегда 0).
        Returns: {"id": str, "apiKey": str, "secret": str, ...}
        """
        if permissions is None:
            permissions = {
                "ContractTrade": ["Order", "Position"],
                "Wallet": ["AccountTransfer"],  # разрешаем только internal transfer
            }

        body = {
            "subuid": int(sub_uid),
            "note": note,
            "readOnly": 0 if not read_only else 1,
            "permissions": permissions,
        }
        data = await self._post("/v5/user/create-sub-api", body)
        result = data["result"]
        logger.info(f"API key created for sub_uid={sub_uid}: key={result.get('apiKey')[:8]}...")
        return result

    # ─── Demo Trading ─────────────────────────────────────────────────────────

    async def create_demo_account(self, uid: str) -> dict[str, Any]:
        """
        Активирует demo trading для суб-аккаунта.
        Bybit Demo Trading использует отдельный endpoint и base URL.
        """
        # Для Demo Trading используем специальный endpoint
        body = {"uid": uid}
        # Note: Demo accounts на Bybit создаются через специальный UI
        # API для создания demo sub-accounts: использует demo base URL
        demo_client = httpx.AsyncClient(
            base_url=settings.bybit_demo_base_url,
            timeout=10.0,
            headers={"Content-Type": "application/json"},
        )
        try:
            body_str = json_lib.dumps(body, separators=(",", ":"))
            timestamp = str(int(time.time() * 1000))
            recv_window = "5000"
            sign_str = f"{timestamp}{self.api_key}{recv_window}{body_str}"
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                sign_str.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": signature,
                "X-BAPI-RECV-WINDOW": recv_window,
                "Content-Type": "application/json",
            }
            resp = await demo_client.post("/v5/user/create-sub-member", content=body_str, headers=headers)
            data = resp.json()
        finally:
            await demo_client.aclose()
        return data.get("result", {})

    async def top_up_demo_balance(
        self,
        uid: str,
        amount: str = "10000",
        coin: str = "USDT",
    ) -> dict[str, Any]:
        """
        Пополняет demo баланс через Bybit Demo Trading API.
        https://bybit-exchange.github.io/docs/v5/demo
        """
        demo_client = httpx.AsyncClient(
            base_url=settings.bybit_demo_base_url,
            timeout=10.0,
        )
        try:
            body = {"adjustType": 0, "utaWalletBalance": amount, "coin": coin}
            body_str = json_lib.dumps(body, separators=(",", ":"))
            timestamp = str(int(time.time() * 1000))
            recv_window = "5000"
            sign_str = f"{timestamp}{self.api_key}{recv_window}{body_str}"
            signature = hmac.new(
                self.api_secret.encode("utf-8"),
                sign_str.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-TIMESTAMP": timestamp,
                "X-BAPI-SIGN": signature,
                "X-BAPI-RECV-WINDOW": recv_window,
                "Content-Type": "application/json",
            }
            resp = await demo_client.post(
                "/v5/account/demo-apply-money",
                content=body_str,
                headers=headers,
            )
            data = resp.json()
            logger.info(f"Demo balance top-up for uid={uid}: {amount} {coin}")
            return data.get("result", {})
        finally:
            await demo_client.aclose()

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
        Внутренний перевод средств на суб-аккаунт funded трейдера.
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

    # ─── Полный процесс создания Demo аккаунта для испытания ─────────────────

    async def setup_demo_challenge_account(
        self,
        account_size: Decimal,
        username_prefix: str,
    ) -> dict[str, Any]:
        """
        Полный процесс создания Demo счёта для испытания:
        1. Создаём суб-аккаунт
        2. Активируем demo trading
        3. Пополняем demo баланс
        4. Создаём API ключи
        Returns: {
            "account_id": str,
            "api_key": str,
            "api_secret": str,
        }
        """
        import secrets
        suffix = secrets.token_hex(4).upper()
        username = f"{username_prefix}_{suffix}"

        # 1. Создать реальный суб-аккаунт (нужен для demo trading)
        sub = await self.create_sub_account(username=username)
        sub_uid = str(sub["uid"])

        # 2. Создать API ключи для demo
        api_result = await self.create_sub_api_key(
            sub_uid=sub_uid,
            note=f"CHM_KRYPTON Demo Challenge {username}",
        )

        # 3. Пополнить demo баланс через demo API
        await self.top_up_demo_balance(
            uid=sub_uid,
            amount=str(account_size),
        )

        logger.info(
            f"Demo challenge account ready: uid={sub_uid}, "
            f"balance={account_size} USDT"
        )
        return {
            "account_id": sub_uid,
            "api_key": api_result["apiKey"],
            "api_secret": api_result["secret"],
        }

    async def setup_funded_account(
        self,
        account_size: Decimal,
        username_prefix: str,
        max_leverage: int = 50,
    ) -> dict[str, Any]:
        """
        Полный процесс создания Real funded счёта:
        1. Создаём real суб-аккаунт
        2. Переводим реальные USDT с master
        3. Создаём API ключи (без прав на вывод)
        Returns: {
            "account_id": str,
            "api_key": str,
            "api_secret": str,
        }
        """
        import secrets
        suffix = secrets.token_hex(4).upper()
        username = f"{username_prefix}_F_{suffix}"

        # 1. Проверяем баланс master
        ok = await self.check_master_balance()
        if not ok:
            raise ValueError("Master balance is below minimum threshold")

        # 2. Создать суб-аккаунт
        sub = await self.create_sub_account(
            username=username,
            note=f"CHM_KRYPTON Funded Account",
        )
        sub_uid = str(sub["uid"])

        # 3. Перевести средства
        await self.internal_transfer(
            amount=str(account_size),
            coin="USDT",
            to_uid=sub_uid,
        )

        # 4. Создать API ключи
        api_result = await self.create_sub_api_key(
            sub_uid=sub_uid,
            note=f"CHM_KRYPTON Funded {username}",
        )

        logger.info(
            f"Funded account ready: uid={sub_uid}, "
            f"balance={account_size} USDT"
        )
        return {
            "account_id": sub_uid,
            "api_key": api_result["apiKey"],
            "api_secret": api_result["secret"],
        }

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
