import asyncio
import json
import logging
import os
from decimal import Decimal

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    Message, WebAppInfo
)
from sqlalchemy import select

from database import AsyncSessionLocal, get_redis
from models import Account, AccountStatus, Trade, TradeStatus, User
from services.pnl_calculator import calculate_win_rate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://t.me/your_bot/app")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Открыть Prop Trading",
                    web_app=WebAppInfo(url=MINI_APP_URL),
                )
            ]
        ]
    )
    await message.answer(
        "👋 <b>Добро пожаловать в Prop Trading!</b>\n\n"
        "📈 Пройди оценку и получи виртуальный торговый счёт.\n\n"
        "<b>Фазы:</b>\n"
        "1️⃣ <b>Evaluation</b> — $10,000, цель +8%\n"
        "2️⃣ <b>Verification</b> — $10,000, цель +5%\n"
        "3️⃣ <b>Funded</b> — торгуй, зарабатывай (80/20 сплит)\n\n"
        "<b>Правила:</b>\n"
        "• Дневная просадка: не более -5%\n"
        "• Общая просадка: не более -10% (trailing)\n"
        "• Минимум 5 торговых дней\n\n"
        "Нажми кнопку ниже, чтобы начать! 👇",
        reply_markup=keyboard,
    )


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Account).where(Account.user_id == user_id)
            .order_by(Account.created_at.desc())
            .limit(1)
        )
        account = result.scalar_one_or_none()

        if not account:
            await message.answer(
                "❌ Аккаунт не найден.\n"
                "Нажми /start чтобы открыть приложение и создать аккаунт."
            )
            return

        balance = Decimal(str(account.current_balance))
        initial = Decimal(str(account.initial_balance))
        profit = balance - initial
        profit_pct = (profit / initial * 100) if initial > 0 else Decimal("0")
        win_rate = calculate_win_rate(account.total_trades, account.winning_trades)

        phase_emoji = {
            "EVALUATION": "1️⃣",
            "VERIFICATION": "2️⃣",
            "FUNDED": "💰",
        }.get(account.phase.value, "❓")

        status_emoji = {
            "ACTIVE": "🟢",
            "PASSED": "✅",
            "FAILED": "🔴",
        }.get(account.status.value, "⚪")

        profit_sign = "+" if profit >= 0 else ""
        profit_color = "📈" if profit >= 0 else "📉"

        text = (
            f"<b>📊 Твоя статистика</b>\n\n"
            f"{phase_emoji} <b>Фаза:</b> {account.phase.value}\n"
            f"{status_emoji} <b>Статус:</b> {account.status.value}\n"
            f"🎯 <b>Попытка:</b> #{account.attempt_number}\n\n"
            f"💵 <b>Баланс:</b> ${balance:,.2f}\n"
            f"{profit_color} <b>Прибыль:</b> {profit_sign}${profit:,.2f} ({profit_sign}{profit_pct:.2f}%)\n"
            f"🎯 <b>Цель:</b> +{account.profit_target_pct}%\n\n"
            f"📆 <b>Торговых дней:</b> {account.trading_days_count}/{account.min_trading_days}\n"
            f"🔢 <b>Сделок:</b> {account.total_trades} (выигрышных: {account.winning_trades})\n"
            f"🏆 <b>Win Rate:</b> {win_rate:.1f}%\n"
        )

        if account.status.value == "FAILED" and account.fail_detail:
            text += f"\n⚠️ <b>Причина провала:</b>\n<i>{account.fail_detail}</i>"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 Открыть приложение",
                        web_app=WebAppInfo(url=MINI_APP_URL),
                    )
                ]
            ]
        )
        await message.answer(text, reply_markup=keyboard)


async def notification_worker():
    """Воркер для обработки уведомлений из Redis очереди."""
    redis = await get_redis()
    logger.info("Notification worker started")

    while True:
        try:
            item = await redis.brpop("bot_notifications", timeout=5)
            if item is None:
                continue

            _, raw = item
            payload = json.loads(raw)
            notification_type = payload.get("type")
            user_id = payload.get("user_id")

            if not user_id:
                continue

            if notification_type == "trade_closed":
                pnl = Decimal(str(payload.get("pnl", "0")))
                symbol = payload.get("symbol", "")
                direction = payload.get("direction", "")
                close_reason = payload.get("close_reason", "")

                reason_text = {
                    "TAKE_PROFIT": "🎯 Take Profit достигнут",
                    "STOP_LOSS": "🛑 Stop Loss сработал",
                    "DAILY_DRAWDOWN": "⚠️ Дневной лимит просадки",
                    "TRAILING_DRAWDOWN": "⚠️ Trailing drawdown",
                    "MANUAL": "✋ Закрыто вручную",
                }.get(close_reason, close_reason)

                pnl_emoji = "✅" if pnl >= 0 else "❌"
                pnl_sign = "+" if pnl >= 0 else ""

                text = (
                    f"{pnl_emoji} <b>Сделка закрыта</b>\n\n"
                    f"📊 {symbol} {direction}\n"
                    f"💰 PnL: <b>{pnl_sign}${pnl:,.2f}</b>\n"
                    f"📝 {reason_text}"
                )
                await bot.send_message(user_id, text)

            elif notification_type == "phase_changed":
                new_phase = payload.get("new_phase", "")
                phase_messages = {
                    "VERIFICATION": (
                        "🎉 <b>Поздравляем! Фаза Evaluation пройдена!</b>\n\n"
                        "Ты переходишь на <b>Verification</b>.\n"
                        "Счёт сброшен до $10,000.\n"
                        "Новая цель: +5% прибыли при соблюдении всех правил."
                    ),
                    "FUNDED": (
                        "🏆 <b>Поздравляем! Ты прошёл все фазы!</b>\n\n"
                        "Ты теперь <b>Funded Trader</b>!\n"
                        "Profit split: 80% тебе / 20% нам.\n"
                        "Торгуй и зарабатывай! 💰"
                    ),
                }
                text = phase_messages.get(new_phase, f"✅ Фаза изменена: {new_phase}")
                await bot.send_message(user_id, text)

            elif notification_type == "account_failed":
                reason = payload.get("reason", "")
                detail = payload.get("detail", "")

                reason_text = {
                    "DAILY_DRAWDOWN_EXCEEDED": "Превышена дневная просадка (-5%)",
                    "TRAILING_DRAWDOWN_EXCEEDED": "Превышена trailing просадка (-10%)",
                }.get(reason, reason)

                text = (
                    f"💔 <b>Аккаунт заблокирован</b>\n\n"
                    f"⚠️ <b>Причина:</b> {reason_text}\n\n"
                    f"<i>{detail}</i>\n\n"
                    f"Открой приложение, чтобы начать новую попытку."
                )
                await bot.send_message(user_id, text)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Notification worker error: {e}")
            await asyncio.sleep(1)


async def main():
    # Запускаем воркер уведомлений параллельно с ботом
    worker_task = asyncio.create_task(notification_worker())
    try:
        await dp.start_polling(bot, allowed_updates=["message"])
    finally:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
