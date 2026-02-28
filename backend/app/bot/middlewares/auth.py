"""
Middleware аутентификации для aiogram.
Проверяет пользователя в БД и создаёт при необходимости.
"""
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject, Update
from loguru import logger
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import generate_referral_code
from app.models.user import User, UserRole


class AuthMiddleware(BaseMiddleware):
    """Middleware для регистрации/обновления пользователя в БД."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Извлекаем telegram user
        tg_user = None
        if isinstance(event, Update):
            if event.message:
                tg_user = event.message.from_user
            elif event.callback_query:
                tg_user = event.callback_query.from_user

        if tg_user:
            async for session in get_db():
                try:
                    result = await session.execute(
                        select(User).where(User.telegram_id == tg_user.id)
                    )
                    user = result.scalar_one_or_none()
                    if not user:
                        user = User(
                            telegram_id=tg_user.id,
                            username=tg_user.username,
                            first_name=tg_user.first_name or "",
                            role=UserRole.guest,
                            referral_code=generate_referral_code(tg_user.id),
                        )
                        session.add(user)
                        await session.commit()
                        logger.info(f"Bot: New user {tg_user.id} registered")
                    else:
                        # Обновляем данные
                        user.username = tg_user.username
                        user.first_name = tg_user.first_name or user.first_name
                        await session.commit()
                    data["db_user"] = user
                    data["session"] = session
                except Exception as e:
                    logger.error(f"AuthMiddleware error: {e}")
                break

        return await handler(event, data)
