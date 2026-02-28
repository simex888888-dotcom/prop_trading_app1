"""
Сервис уведомлений — отправляет сообщения через Telegram Bot API
и сохраняет уведомления в БД.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.notification import Notification

if TYPE_CHECKING:
    from app.models.challenge import UserChallenge


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._bot = None

    def _get_bot(self):
        if self._bot is None:
            from aiogram import Bot
            self._bot = Bot(token=settings.telegram_bot_token)
        return self._bot

    async def _send_telegram(self, telegram_id: int, text: str, parse_mode: str = "HTML") -> None:
        """Отправляет сообщение в Telegram."""
        if not settings.telegram_bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not set, skipping notification")
            return
        try:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

            bot = self._get_bot()
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(
                        text="📱 Открыть CHM_KRYPTON",
                        web_app=WebAppInfo(url=settings.telegram_webapp_url),
                    )
                ]]
            )
            await bot.send_message(
                chat_id=telegram_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=keyboard,
            )
        except Exception as e:
            logger.error(f"Failed to send Telegram notification to {telegram_id}: {e}")

    async def _save_notification(
        self,
        user_id: int,
        notification_type: str,
        title: str,
        body: str,
    ) -> None:
        """Сохраняет уведомление в БД."""
        notif = Notification(
            user_id=user_id,
            type=notification_type,
            title=title,
            body=body,
            is_read=False,
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(notif)

    async def _notify(
        self,
        challenge: "UserChallenge",
        notification_type: str,
        title: str,
        body: str,
    ) -> None:
        """Сохраняет + отправляет уведомление."""
        await self._save_notification(
            user_id=challenge.user_id,
            notification_type=notification_type,
            title=title,
            body=body,
        )
        telegram_id = challenge.user.telegram_id
        await self._send_telegram(telegram_id, f"<b>{title}</b>\n\n{body}")

    # ─── Конкретные уведомления ───────────────────────────────────────────────

    async def send_challenge_purchased(self, challenge: "UserChallenge") -> None:
        await self._notify(
            challenge,
            "challenge_purchased",
            "✅ Испытание активировано!",
            f"Счёт #{challenge.id} активирован. Начальный баланс: "
            f"<b>${challenge.initial_balance:,.0f}</b>\n\nУдачи на пути, элемент!",
        )

    async def send_goal_50_notification(
        self, challenge: "UserChallenge", current_pct: Decimal
    ) -> None:
        await self._notify(
            challenge,
            "goal_50_pct",
            "🎯 Ты уже на полпути!",
            f"Прибыль: <b>{current_pct:.1f}%</b>. Держи темп, трейдер.",
        )

    async def send_goal_80_notification(
        self, challenge: "UserChallenge", current_pct: Decimal
    ) -> None:
        await self._notify(
            challenge,
            "goal_80_pct",
            "🔥 До цели совсем чуть-чуть!",
            f"Прибыль: <b>{current_pct:.1f}%</b>. Не торопись — будь точен.",
        )

    async def send_daily_drawdown_warning(self, challenge: "UserChallenge") -> None:
        await self._notify(
            challenge,
            "daily_drawdown_80",
            "⚠️ Предупреждение о просадке",
            "Ты достиг 80% дневного лимита просадки. Будь осторожен!",
        )

    async def send_total_drawdown_warning(self, challenge: "UserChallenge") -> None:
        await self._notify(
            challenge,
            "total_drawdown_80",
            "🚨 Критический уровень просадки!",
            "Общая просадка достигла 80% лимита. Рекомендуем приостановить торговлю.",
        )

    async def send_violation_notification(
        self, challenge: "UserChallenge", violation: dict
    ) -> None:
        await self._notify(
            challenge,
            "violation",
            "❌ Счёт закрыт — нарушение правил",
            f"Причина: <b>{violation['description']}</b>\n\n"
            f"Детали доступны в приложении. Ты можешь начать новое испытание!",
        )

    async def send_phase1_passed_notification(self, challenge: "UserChallenge") -> None:
        await self._notify(
            challenge,
            "phase1_passed",
            "🏆 Фаза 1 пройдена!",
            "Отличная работа! Ты переходишь в Фазу 2. "
            "Новые условия и новые возможности ждут тебя.",
        )

    async def send_funded_notification(self, challenge: "UserChallenge") -> None:
        await self._notify(
            challenge,
            "funded",
            "💎 Поздравляем! Финансирование получено!",
            f"Ты достиг статуса <b>Funded Trader</b>!\n"
            f"Размер счёта: <b>${challenge.initial_balance:,.0f}</b>\n"
            f"Торгуй реальными деньгами — ты это заслужил!",
        )

    async def send_payout_approved(
        self, challenge: "UserChallenge", amount: Decimal
    ) -> None:
        await self._notify(
            challenge,
            "payout_approved",
            "💰 Выплата отправлена!",
            f"Выплата <b>${amount:,.2f}</b> отправлена на твой кошелёк.",
        )

    async def send_payout_rejected(
        self, challenge: "UserChallenge", reason: Optional[str] = None
    ) -> None:
        reason_text = f"\nПричина: {reason}" if reason else ""
        await self._notify(
            challenge,
            "payout_rejected",
            "❌ Выплата отклонена",
            f"Запрос на выплату был отклонён.{reason_text}\n"
            "Свяжитесь с поддержкой для уточнения.",
        )

    async def send_achievement_notification(
        self,
        challenge: "UserChallenge",
        achievement_name: str,
        level: str,
    ) -> None:
        await self._notify(
            challenge,
            "achievement",
            "🏅 Новое достижение!",
            f"Ты разблокировал: <b>{achievement_name}</b> ({level})\n"
            "Заходи в приложение, чтобы посмотреть!",
        )

    async def send_scaling_notification(
        self,
        challenge: "UserChallenge",
        old_size: Decimal,
        new_size: Decimal,
    ) -> None:
        await self._notify(
            challenge,
            "scaling",
            "📈 Счёт увеличен!",
            f"Твои результаты заслуживают большего!\n"
            f"Счёт увеличен с <b>${old_size:,.0f}</b> до <b>${new_size:,.0f}</b>",
        )

    async def send_to_super_admin(self, message: str) -> None:
        """Отправляет уведомление super_admin."""
        if not settings.super_admin_tg_id:
            return
        await self._send_telegram(settings.super_admin_tg_id, message)
