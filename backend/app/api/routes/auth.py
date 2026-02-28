"""
/auth — авторизация через Telegram initData, JWT токены.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_referral_code,
    validate_telegram_init_data,
)
from app.models.user import User, UserRole
from app.schemas.common import APIResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class TelegramAuthRequest(BaseModel):
    init_data: str
    referral_code: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    role: str
    is_new: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


from typing import Optional


@router.post("/telegram", response_model=APIResponse[TokenResponse])
async def auth_telegram(
    body: TelegramAuthRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse[TokenResponse]:
    """
    Валидирует Telegram initData и выдаёт JWT токены.
    Если пользователь новый — создаёт запись.
    """
    try:
        tg_data = validate_telegram_init_data(
            body.init_data, settings.telegram_bot_token
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    tg_user = tg_data["user"]
    telegram_id = int(tg_user["id"])
    start_param = tg_data.get("start_param")  # реферальный код

    # Ищем или создаём пользователя
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    is_new = user is None

    if is_new:
        referral_code = generate_referral_code(telegram_id)
        referred_by: Optional[int] = None

        # Обработка реферального кода
        ref_code = body.referral_code or start_param
        if ref_code:
            ref_stmt = select(User).where(User.referral_code == ref_code)
            ref_result = await session.execute(ref_stmt)
            referrer = ref_result.scalar_one_or_none()
            if referrer and referrer.telegram_id != telegram_id:
                referred_by = referrer.id

        user = User(
            telegram_id=telegram_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name", ""),
            avatar_url=None,
            role=UserRole.guest,
            referral_code=referral_code,
            referred_by=referred_by,
        )
        session.add(user)
        await session.flush()  # получаем user.id
        logger.info(f"New user registered: telegram_id={telegram_id} id={user.id}")
    else:
        # Обновляем данные
        user.username = tg_user.get("username", user.username)
        user.first_name = tg_user.get("first_name", user.first_name)

    await session.commit()

    # Создаём JWT
    token_data = {"sub": str(user.id), "tg": telegram_id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return APIResponse(
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            role=user.role,
            is_new=is_new,
        )
    )


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh_tokens(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db),
) -> APIResponse[TokenResponse]:
    """Обновляет access + refresh токены."""
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    stmt = select(User).where(User.id == int(user_id))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or user.is_blocked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or blocked")

    token_data = {"sub": str(user.id), "tg": user.telegram_id}
    return APIResponse(
        data=TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
            user_id=user.id,
            role=user.role,
        )
    )
