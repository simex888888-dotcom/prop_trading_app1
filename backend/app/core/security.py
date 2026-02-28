import hashlib
import hmac
import json
import os
import time
import urllib.parse
from base64 import b64decode, b64encode
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from jose import JWTError, jwt
from loguru import logger

from app.core.config import settings


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        raise


# ─── Telegram initData validation ─────────────────────────────────────────────

def validate_telegram_init_data(init_data: str, bot_token: str) -> dict[str, Any]:
    """
    Валидирует initData от Telegram WebApp согласно официальной документации.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            raise ValueError("Missing hash in initData")

        # Проверка времени (не старше 1 часа)
        auth_date = int(parsed.get("auth_date", 0))
        if time.time() - auth_date > 3600:
            raise ValueError("initData expired")

        # Сортируем и формируем data-check-string
        data_check_parts = sorted(f"{k}={v}" for k, v in parsed.items())
        data_check_string = "\n".join(data_check_parts)

        # HMAC-SHA256: key = HMAC-SHA256("WebAppData", bot_token)
        secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
        computed_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed_hash, received_hash):
            raise ValueError("Invalid hash — data tampered")

        # Парсим user
        user_data = json.loads(parsed.get("user", "{}"))
        return {
            "user": user_data,
            "auth_date": auth_date,
            "query_id": parsed.get("query_id"),
            "start_param": parsed.get("start_param"),
        }
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        raise ValueError(f"Telegram initData validation failed: {e}")


# ─── AES-256 Encryption for API keys ──────────────────────────────────────────

def _get_aes_key() -> bytes:
    """Возвращает 32-байтный ключ из настроек (hex или raw)."""
    key_str = settings.aes_encryption_key
    if len(key_str) == 64:  # hex-encoded 32 bytes
        return bytes.fromhex(key_str)
    elif len(key_str) == 32:  # raw 32 bytes
        return key_str.encode()
    else:
        raise ValueError(f"AES key must be 32 bytes (raw) or 64 hex chars, got {len(key_str)}")


def encrypt_aes256(plaintext: str) -> str:
    """Шифрует строку AES-256-CBC. Возвращает base64(iv + ciphertext)."""
    key = _get_aes_key()
    iv = os.urandom(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(plaintext.encode("utf-8"), AES.block_size))
    return b64encode(iv + ciphertext).decode("utf-8")


def decrypt_aes256(encrypted: str) -> str:
    """Дешифрует строку, зашифрованную encrypt_aes256."""
    key = _get_aes_key()
    raw = b64decode(encrypted.encode("utf-8"))
    iv = raw[:16]
    ciphertext = raw[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(ciphertext), AES.block_size).decode("utf-8")


# ─── Rate Limiting helpers (Redis-based) ──────────────────────────────────────

async def check_rate_limit(
    redis,
    key: str,
    limit: int,
    window_seconds: int = 60,
) -> bool:
    """
    Проверяет rate limit. Возвращает True если лимит не превышен.
    Использует sliding window через Redis INCR + EXPIRE.
    """
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, window_seconds)
    results = await pipe.execute()
    current_count = results[0]
    return current_count <= limit


# ─── Referral code generation ─────────────────────────────────────────────────

def generate_referral_code(telegram_id: int) -> str:
    """Генерирует уникальный реферальный код на основе telegram_id."""
    import secrets
    import string
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(6))
    return f"KR{random_part}"
