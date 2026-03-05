"""
Обработчики команд Telegram бота CHM_KRYPTON.
"""
from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.bot.keyboards.main import (
    get_main_menu_keyboard,
    get_open_app_keyboard,
    get_support_keyboard,
)
from app.core.config import settings
from app.models.challenge import ChallengeStatus, UserChallenge
from app.models.user import User

router = Router(name="commands")

ONBOARDING_TEXT = """
⚗️ <b>CHM_KRYPTON</b> — Trade Like an Element

Добро пожаловать на платформу крипто проп-трейдинга нового поколения.

🧬 <b>Твой путь:</b>
Isotope → Reagent → Catalyst → Molecule → Crystal → Nucleus → <b>Krypton</b>

💎 <b>Что тебя ждёт:</b>
• Demo-испытание на счёте от $5,000 до $200,000
• Прохождение — получаешь реальный funded аккаунт
• Профит-шер до <b>90%</b> от заработка
• Масштабирование счёта до <b>$2,000,000</b>

🚀 Нажми кнопку ниже, чтобы начать свой путь элемента.
"""


@router.message(CommandStart())
async def cmd_start(message: Message, db_user: User) -> None:
    """Команда /start — приветствие."""
    if db_user.is_blocked:
        await message.answer("❌ Ваш аккаунт заблокирован. Обратитесь в поддержку.")
        return

    await message.answer(
        ONBOARDING_TEXT,
        parse_mode="HTML",
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("balance"))
async def cmd_balance(message: Message, db_user: User, session: AsyncSession) -> None:
    """Команда /balance — быстрый баланс."""
    result = await session.execute(
        select(UserChallenge)
        .where(
            UserChallenge.user_id == db_user.id,
            UserChallenge.status.in_([
                ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded
            ]),
        )
        .options(selectinload(UserChallenge.challenge_type))
        .order_by(UserChallenge.created_at.desc())
    )
    challenge = result.scalars().first()

    if not challenge:
        await message.answer(
            "У тебя нет активных испытаний. Открой приложение и начни!",
            reply_markup=get_open_app_keyboard(),
        )
        return

    ct = challenge.challenge_type
    mode_badge = "🟡 DEMO" if challenge.account_mode == "demo" else "🟢 FUNDED"
    pnl = float(challenge.total_pnl)
    pnl_pct = (pnl / float(challenge.initial_balance) * 100) if challenge.initial_balance else 0
    pnl_emoji = "📈" if pnl >= 0 else "📉"

    text = (
        f"💼 <b>Счёт #{challenge.id}</b> {mode_badge}\n\n"
        f"💰 <b>Баланс:</b> ${float(challenge.current_balance):,.2f}\n"
        f"{pnl_emoji} <b>PnL:</b> ${pnl:+,.2f} ({pnl_pct:+.2f}%)\n"
        f"📅 <b>Торговых дней:</b> {challenge.trading_days_count}/{ct.min_trading_days}\n"
        f"🎯 <b>Цель:</b> ${float(challenge.initial_balance) * float(ct.profit_target_p1) / 100:,.2f}"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=get_open_app_keyboard())


@router.message(Command("stats"))
async def cmd_stats(message: Message, db_user: User, session: AsyncSession) -> None:
    """Команда /stats — краткая статистика."""
    result = await session.execute(
        select(UserChallenge)
        .where(
            UserChallenge.user_id == db_user.id,
            UserChallenge.status.in_([
                ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded
            ]),
        )
        .options(selectinload(UserChallenge.challenge_type))
        .order_by(UserChallenge.created_at.desc())
    )
    challenge = result.scalars().first()

    if not challenge:
        await message.answer("Нет активных испытаний.", reply_markup=get_open_app_keyboard())
        return

    ct = challenge.challenge_type
    daily_pnl = float(challenge.daily_pnl)
    total_pnl = float(challenge.total_pnl)
    initial = float(challenge.initial_balance)
    daily_dd_limit = float(ct.max_daily_loss)
    daily_start = float(challenge.daily_start_balance)
    daily_dd = max(0, -daily_pnl / daily_start * 100) if daily_start else 0
    total_dd = max(0, -total_pnl / initial * 100) if initial else 0

    text = (
        f"📊 <b>Статистика испытания #{challenge.id}</b>\n\n"
        f"💰 <b>Дневной PnL:</b> ${daily_pnl:+,.2f}\n"
        f"💎 <b>Общий PnL:</b> ${total_pnl:+,.2f}\n\n"
        f"⚠️ <b>Дневная просадка:</b> {daily_dd:.1f}% / {daily_dd_limit:.1f}%\n"
        f"🚨 <b>Общая просадка:</b> {total_dd:.1f}% / {float(ct.max_total_loss):.1f}%\n\n"
        f"📅 <b>Торговых дней:</b> {challenge.trading_days_count}\n"
        f"🔥 <b>Streak:</b> {db_user.streak_days} дней"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=get_open_app_keyboard())


@router.message(Command("rules"))
async def cmd_rules(message: Message, db_user: User, session: AsyncSession) -> None:
    """Команда /rules — правила текущего испытания."""
    result = await session.execute(
        select(UserChallenge)
        .where(
            UserChallenge.user_id == db_user.id,
            UserChallenge.status.in_([
                ChallengeStatus.phase1, ChallengeStatus.phase2, ChallengeStatus.funded
            ]),
        )
        .options(selectinload(UserChallenge.challenge_type))
        .order_by(UserChallenge.created_at.desc())
    )
    challenge = result.scalars().first()

    if not challenge:
        await message.answer("Нет активных испытаний.", reply_markup=get_open_app_keyboard())
        return

    ct = challenge.challenge_type
    text = (
        f"📋 <b>Правила испытания {ct.name}</b>\n\n"
        f"🎯 <b>Цель прибыли:</b> {float(ct.profit_target_p1):.0f}%\n"
        f"⛔ <b>Макс. дневная просадка:</b> {float(ct.max_daily_loss):.0f}%\n"
        f"⛔ <b>Макс. общая просадка:</b> {float(ct.max_total_loss):.0f}%\n"
        f"📅 <b>Минимум торговых дней:</b> {ct.min_trading_days}\n"
        f"📐 <b>Тип просадки:</b> {'Trailing' if ct.drawdown_type == 'trailing' else 'Static'}\n"
        f"⚖️ <b>Консистентность:</b> {'Да' if ct.consistency_rule else 'Нет'}\n"
        f"🔧 <b>Макс. плечо:</b> {ct.max_leverage}x\n"
        f"💰 <b>Профит-шер:</b> {float(ct.profit_split_pct):.0f}%"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=get_open_app_keyboard())


@router.message(Command("payout"))
async def cmd_payout(message: Message, db_user: User) -> None:
    """Команда /payout — запрос выплаты через приложение."""
    await message.answer(
        "💳 <b>Запрос выплаты</b>\n\n"
        "Для запроса выплаты откройте приложение и перейдите в раздел «Выплаты».",
        parse_mode="HTML",
        reply_markup=get_open_app_keyboard("💳 Открыть раздел выплат"),
    )


@router.message(Command("support"))
async def cmd_support(message: Message) -> None:
    """Команда /support — связь с поддержкой."""
    await message.answer(
        "❓ <b>Поддержка CHM_KRYPTON</b>\n\n"
        "Наша команда готова помочь вам. Напишите нам:",
        parse_mode="HTML",
        reply_markup=get_support_keyboard(),
    )


@router.message(Command("referral"))
async def cmd_referral(message: Message, db_user: User) -> None:
    """Команда /referral — реферальные данные."""
    ref_link = (
        f"https://t.me/{settings.telegram_bot_username}"
        f"?start={db_user.referral_code}"
    )
    text = (
        f"👥 <b>Реферальная программа</b>\n\n"
        f"🔗 <b>Твоя ссылка:</b>\n<code>{ref_link}</code>\n\n"
        f"💰 <b>Вознаграждение:</b>\n"
        f"• Уровень 1: 10% от покупки реферала\n"
        f"• Уровень 2: 3% от покупки реферала реферала\n\n"
        f"Выплаты — каждые 7 дней автоматически."
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_open_app_keyboard())


# ─── Обработчик скриншота оплаты ──────────────────────────────────────────────

@router.message(F.photo)
async def handle_payment_screenshot(
    message: Message,
    db_user: User,
    session: AsyncSession,
) -> None:
    """
    Когда пользователь отправляет фото — проверяем pending_payment испытание.
    Если есть — пересылаем скриншот администраторам с кнопками Подтвердить/Отклонить.
    """
    result = await session.execute(
        select(UserChallenge)
        .where(
            UserChallenge.user_id == db_user.id,
            UserChallenge.status == ChallengeStatus.pending_payment,
        )
        .order_by(UserChallenge.created_at.desc())
    )
    challenge = result.scalars().first()

    if not challenge:
        await message.answer(
            "📸 Фото получено. Если хотите оплатить испытание — сначала выберите план в приложении.",
            reply_markup=get_open_app_keyboard(),
        )
        return

    user_display = f"@{db_user.username}" if db_user.username else f"tg:{db_user.telegram_id}"
    caption = (
        f"📸 <b>Скриншот оплаты!</b>\n\n"
        f"👤 {user_display}\n"
        f"🆔 Challenge ID: <code>{challenge.id}</code>\n\n"
        f"Проверьте оплату и нажмите кнопку:"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"adm:approve_challenge:{challenge.id}",
        ),
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"adm:reject_challenge:{challenge.id}",
        ),
    ]])

    from aiogram import Bot
    bot = Bot(token=settings.telegram_bot_token)
    photo_id = message.photo[-1].file_id

    forwarded = 0
    for admin_id in settings.admin_tg_ids:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            forwarded += 1
        except Exception as e:
            logger.warning(f"Could not forward screenshot to admin {admin_id}: {e}")
    await bot.session.close()

    if forwarded > 0:
        await message.answer(
            "✅ <b>Скриншот получен и отправлен администраторам!</b>\n\n"
            "Ожидайте подтверждения — обычно это занимает до 24 часов.",
            parse_mode="HTML",
        )
    else:
        await message.answer("⚠️ Не удалось уведомить администраторов. Напишите в поддержку.")
