"""
Точка входа Telegram бота CHM_KRYPTON (aiogram 3.x).
"""
import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from app.core.config import settings
from app.bot.handlers import commands, callbacks, admin_bot
from app.bot.middlewares.auth import AuthMiddleware


async def main() -> None:
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set!")
        sys.exit(1)

    bot = Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Middleware
    dp.update.middleware(AuthMiddleware())

    # Роутеры
    dp.include_router(admin_bot.router)   # Admin panel — первым, чтобы перехватывать /adm*
    dp.include_router(commands.router)
    dp.include_router(callbacks.router)

    logger.info(f"Starting CHM_KRYPTON bot @{settings.telegram_bot_username}")

    # Give Railway ~5 s to SIGTERM the previous container before we start polling.
    # Without this delay, the old container's retry loop kicks us out first.
    logger.info("Waiting 5 s for previous instance to shut down...")
    await asyncio.sleep(5)

    # Drop any webhook and stale updates left by the old instance.
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Webhook cleared, starting polling...")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=["message", "callback_query", "inline_query"],
            drop_pending_updates=True,
        )
    finally:
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
