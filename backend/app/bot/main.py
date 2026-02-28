"""
Точка входа Telegram бота CHM_KRYPTON (aiogram 3.x).
"""
import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from loguru import logger

from app.core.config import settings
from app.bot.handlers import commands, callbacks
from app.bot.middlewares.auth import AuthMiddleware


async def main() -> None:
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set!")
        sys.exit(1)

    bot = Bot(
        token=settings.telegram_bot_token,
        parse_mode=ParseMode.HTML,
    )
    dp = Dispatcher()

    # Middleware
    dp.update.middleware(AuthMiddleware())

    # Роутеры
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)

    logger.info(f"Starting CHM_KRYPTON bot @{settings.telegram_bot_username}")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
