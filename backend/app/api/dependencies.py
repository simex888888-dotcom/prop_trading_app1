"""
FastAPI зависимости: аутентификация, авторизация, rate limiting.
"""
from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_redis
from app.core.security import check_rate_limit, decode_token
from app.models.user import User, UserRole

# ─── Получение текущего пользователя ──────────────────────────────────────────

async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
    session: AsyncSession = Depends(get_db),
) -> User:
    """Извлекает пользователя из JWT токена."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing or invalid",
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    stmt = select(User).where(User.id == int(user_id))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if user.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is blocked")

    return user


# ─── Ограничение доступа по ролям ─────────────────────────────────────────────

def require_role(*roles: UserRole):
    """Фабрика зависимостей для проверки ролей."""
    async def _check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {[r.value for r in roles]}",
            )
        return user
    return _check


def require_admin():
    return require_role(UserRole.admin, UserRole.super_admin)


def require_super_admin():
    return require_role(UserRole.super_admin)


def require_funded():
    return require_role(
        UserRole.funded_trader,
        UserRole.elite_trader,
        UserRole.admin,
        UserRole.super_admin,
    )


# ─── Rate limiting ────────────────────────────────────────────────────────────

async def rate_limit_standard(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    """100 запросов в минуту на пользователя."""
    from app.core.config import settings
    redis = await get_redis()
    key = f"rate:std:{user.id}"
    allowed = await check_rate_limit(redis, key, limit=settings.rate_limit_per_minute)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Try again in a minute.",
        )


async def rate_limit_trading(
    request: Request,
    user: User = Depends(get_current_user),
) -> None:
    """10 запросов в минуту на торговые эндпоинты."""
    from app.core.config import settings
    redis = await get_redis()
    key = f"rate:trade:{user.id}"
    allowed = await check_rate_limit(redis, key, limit=settings.rate_limit_trading_per_minute)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trading rate limit exceeded. Try again in a minute.",
        )
