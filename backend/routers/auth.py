import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qsl, unquote

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, get_redis
from models import Account, AccountPhase, AccountStatus, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_TTL = 86400 * 7  # 7 дней


class InitDataRequest(BaseModel):
    init_data: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    first_name: str
    username: Optional[str]
    account_id: int
    phase: str
    status: str


def validate_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """
    Валидация initData от Telegram Mini App по алгоритму HMAC-SHA256.
    https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
    """
    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)

    if not received_hash:
        raise ValueError("hash отсутствует в initData")

    # Строка для проверки — отсортированные пары key=value через \n
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(parsed.items())
    )

    # Секретный ключ = HMAC-SHA256("WebAppData", bot_token)
    secret_key = hmac.new(
        b"WebAppData", bot_token.encode(), hashlib.sha256
    ).digest()

    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("Невалидная подпись initData")

    # Проверка свежести данных (не старше 1 часа)
    auth_date = int(parsed.get("auth_date", 0))
    now = int(datetime.now(timezone.utc).timestamp())
    if now - auth_date > 3600:
        raise ValueError("initData устарел (>1 часа)")

    user_json = parsed.get("user")
    if not user_json:
        raise ValueError("user отсутствует в initData")

    user_data = json.loads(unquote(user_json))
    return user_data


async def get_current_user(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> tuple[User, Account]:
    """Dependency для защищённых эндпоинтов."""
    redis = await get_redis()
    session_key = f"session:{token}"
    user_id_str = await redis.get(session_key)

    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия не найдена или устарела")

    user_id = int(user_id_str)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")

    result = await db.execute(
        select(Account).where(
            Account.user_id == user_id,
        ).order_by(Account.created_at.desc()).limit(1)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аккаунт не найден")

    # Обновляем TTL сессии при активности
    await redis.expire(session_key, SESSION_TTL)

    return user, account


@router.post("/telegram", response_model=AuthResponse)
async def auth_telegram(
    body: InitDataRequest,
    db: AsyncSession = Depends(get_db),
):
    """Авторизация через Telegram initData. Создаёт пользователя и аккаунт при первом входе."""
    try:
        user_data = validate_telegram_init_data(body.init_data, BOT_TOKEN)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    telegram_id = int(user_data["id"])
    first_name = user_data.get("first_name", "Trader")
    last_name = user_data.get("last_name")
    username = user_data.get("username")

    # Upsert пользователя
    result = await db.execute(select(User).where(User.id == telegram_id))
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        db.add(user)
        await db.flush()
    else:
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        db.add(user)

    # Получаем активный аккаунт (последний)
    result = await db.execute(
        select(Account).where(Account.user_id == telegram_id)
        .order_by(Account.created_at.desc())
        .limit(1)
    )
    account = result.scalar_one_or_none()

    if not account:
        now_utc = datetime.now(timezone.utc)
        account = Account(
            user_id=telegram_id,
            phase=AccountPhase.EVALUATION,
            status=AccountStatus.ACTIVE,
            day_start_date=now_utc.replace(hour=0, minute=0, second=0, microsecond=0),
        )
        db.add(account)
        await db.flush()

    await db.commit()
    await db.refresh(account)

    # Создаём сессию в Redis
    import secrets
    token = secrets.token_hex(32)
    redis = await get_redis()
    await redis.setex(f"session:{token}", SESSION_TTL, str(telegram_id))

    return AuthResponse(
        token=token,
        user_id=telegram_id,
        first_name=first_name,
        username=username,
        account_id=account.id,
        phase=account.phase.value,
        status=account.status.value,
    )
