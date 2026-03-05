"""
Telegram Admin Panel — только для администраторов CHM_KRYPTON.
Доступен для Telegram ID из settings.admin_tg_ids (445677777, 705020259).

Команды:
  /adm — главное меню
  /adm_stats — быстрая статистика
  /adm_payouts — ожидающие выплаты
  /adm_users — последние пользователи
"""
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.challenge import ChallengeStatus, ChallengeType, UserChallenge
from app.models.payout import Payout, PayoutStatus
from app.models.user import User, UserRole

router = Router(name="admin_bot")


# ─── Проверка прав ─────────────────────────────────────────────────────────────

def _is_admin(tg_id: int) -> bool:
    return tg_id in settings.admin_tg_ids


def _admin_only(message: Message) -> bool:
    """Отправляет отказ и возвращает False если не администратор."""
    return _is_admin(message.from_user.id)


# ─── Клавиатуры ────────────────────────────────────────────────────────────────

def _main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats"),
            InlineKeyboardButton(text="💰 Выплаты", callback_data="adm:payouts"),
        ],
        [
            InlineKeyboardButton(text="👥 Пользователи", callback_data="adm:users"),
            InlineKeyboardButton(text="⚡ Активировать", callback_data="adm:activate_prompt"),
        ],
        [
            InlineKeyboardButton(text="🔄 Обновить", callback_data="adm:refresh"),
        ],
    ])


def _payout_action_kb(payout_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Одобрить",
                callback_data=f"adm:approve_payout:{payout_id}",
            ),
            InlineKeyboardButton(
                text="❌ Отклонить",
                callback_data=f"adm:reject_payout:{payout_id}",
            ),
        ],
    ])


def _back_to_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Главное меню", callback_data="adm:menu")],
    ])


# ─── Вспомогательные ──────────────────────────────────────────────────────────

async def _get_stats_text(session: AsyncSession) -> str:
    total_users = (await session.execute(select(func.count(User.id)))).scalar() or 0

    active_chal = (await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.status.in_([ChallengeStatus.phase1, ChallengeStatus.phase2])
        )
    )).scalar() or 0

    funded = (await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.status == ChallengeStatus.funded
        )
    )).scalar() or 0

    failed = (await session.execute(
        select(func.count(UserChallenge.id)).where(
            UserChallenge.status == ChallengeStatus.failed
        )
    )).scalar() or 0

    pending_count = (await session.execute(
        select(func.count(Payout.id)).where(Payout.status == PayoutStatus.pending)
    )).scalar() or 0

    pending_amt = (await session.execute(
        select(func.sum(Payout.amount)).where(Payout.status == PayoutStatus.pending)
    )).scalar() or 0

    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    return (
        f"📊 <b>CHM_KRYPTON — Панель администратора</b>\n"
        f"<i>{now}</i>\n\n"
        f"👥 <b>Пользователей:</b> {total_users}\n"
        f"⚔️ <b>Активных испытаний:</b> {active_chal}\n"
        f"💎 <b>Funded трейдеров:</b> {funded}\n"
        f"❌ <b>Провалено:</b> {failed}\n\n"
        f"💰 <b>Ожидают выплат:</b> {pending_count} шт. / <b>${float(pending_amt):.2f}</b>"
    )


# ─── Команды ──────────────────────────────────────────────────────────────────

@router.message(Command("adm"))
async def cmd_adm(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message):
        return
    text = await _get_stats_text(session)
    await message.answer(text, parse_mode="HTML", reply_markup=_main_menu_kb())


@router.message(Command("adm_stats"))
async def cmd_adm_stats(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message):
        return
    text = await _get_stats_text(session)
    await message.answer(text, parse_mode="HTML", reply_markup=_back_to_menu_kb())


@router.message(Command("adm_payouts"))
async def cmd_adm_payouts(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message):
        return
    await _send_pending_payouts(message, session)


@router.message(Command("adm_users"))
async def cmd_adm_users(message: Message, session: AsyncSession) -> None:
    if not _admin_only(message):
        return
    await _send_user_list(message, session)


async def _send_pending_payouts(message: Message, session: AsyncSession) -> None:
    result = await session.execute(
        select(Payout, User)
        .join(User, Payout.user_id == User.id)
        .where(Payout.status == PayoutStatus.pending)
        .order_by(Payout.requested_at)
        .limit(10)
    )
    rows = result.all()

    if not rows:
        await message.answer(
            "✅ <b>Нет ожидающих выплат</b>",
            parse_mode="HTML",
            reply_markup=_back_to_menu_kb(),
        )
        return

    await message.answer(
        f"💰 <b>Ожидающие выплаты ({len(rows)})</b>",
        parse_mode="HTML",
    )
    for payout, user in rows:
        uname = f"@{user.username}" if user.username else f"ID {user.telegram_id}"
        req_date = payout.requested_at.strftime("%d.%m %H:%M") if payout.requested_at else "—"
        text = (
            f"💸 <b>Выплата #{payout.id}</b>\n"
            f"👤 {uname} (challenge #{payout.challenge_id})\n"
            f"💵 <b>${float(payout.amount):.2f}</b> → {payout.network}\n"
            f"🏦 <code>{payout.wallet_address}</code>\n"
            f"📅 {req_date}"
        )
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=_payout_action_kb(payout.id),
        )


async def _send_user_list(message: Message, session: AsyncSession) -> None:
    result = await session.execute(
        select(User).order_by(User.created_at.desc()).limit(10)
    )
    users = result.scalars().all()
    if not users:
        await message.answer("👥 Пользователей пока нет.", reply_markup=_back_to_menu_kb())
        return

    lines = ["👥 <b>Последние пользователи</b>\n"]
    for u in users:
        uname = f"@{u.username}" if u.username else u.first_name
        blocked = " 🔒" if u.is_blocked else ""
        lines.append(
            f"• {uname}{blocked} | <code>{u.telegram_id}</code> | "
            f"{u.role.value if hasattr(u.role, 'value') else u.role}"
        )
    lines.append("\n<i>Чтобы заблокировать: /adm_block &lt;tg_id&gt;</i>")
    lines.append("<i>Чтобы активировать испытание: /adm_activate &lt;tg_id&gt; &lt;size&gt;</i>")

    await message.answer(
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=_back_to_menu_kb(),
    )


# ─── Команда блокировки ────────────────────────────────────────────────────────

@router.message(Command("adm_block"))
async def cmd_adm_block(message: Message, session: AsyncSession) -> None:
    """Блокировка: /adm_block <tg_id>"""
    if not _admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Использование: /adm_block &lt;telegram_id&gt;", parse_mode="HTML")
        return
    tg_id = int(parts[1])
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer(f"❌ Пользователь {tg_id} не найден.")
        return
    if user.role == UserRole.super_admin:
        await message.answer("❌ Нельзя заблокировать super_admin.")
        return
    user.is_blocked = True
    await session.commit()
    uname = f"@{user.username}" if user.username else user.first_name
    await message.answer(f"🔒 Пользователь {uname} (<code>{tg_id}</code>) заблокирован.", parse_mode="HTML")


@router.message(Command("adm_unblock"))
async def cmd_adm_unblock(message: Message, session: AsyncSession) -> None:
    """Разблокировка: /adm_unblock <tg_id>"""
    if not _admin_only(message):
        return
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].lstrip("-").isdigit():
        await message.answer("Использование: /adm_unblock &lt;telegram_id&gt;", parse_mode="HTML")
        return
    tg_id = int(parts[1])
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer(f"❌ Пользователь {tg_id} не найден.")
        return
    user.is_blocked = False
    await session.commit()
    uname = f"@{user.username}" if user.username else user.first_name
    await message.answer(f"✅ Пользователь {uname} (<code>{tg_id}</code>) разблокирован.", parse_mode="HTML")


# ─── Ручная активация испытания ────────────────────────────────────────────────

@router.message(Command("adm_activate"))
async def cmd_adm_activate(message: Message, session: AsyncSession) -> None:
    """
    Ручная активация испытания после подтверждения оплаты.
    Использование: /adm_activate <tg_id> <account_size>
    Пример: /adm_activate 123456789 10000
    """
    if not _admin_only(message):
        return

    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(
            "Использование: /adm_activate &lt;telegram_id&gt; &lt;размер_счёта&gt;\n"
            "Пример: <code>/adm_activate 123456789 10000</code>",
            parse_mode="HTML",
        )
        return

    tg_id_str, size_str = parts[1], parts[2]
    if not tg_id_str.lstrip("-").isdigit() or not size_str.replace(".", "").isdigit():
        await message.answer("❌ Неверный формат. tg_id и размер счёта должны быть числами.")
        return

    tg_id = int(tg_id_str)
    account_size = float(size_str)

    # Найти пользователя
    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()
    if not user:
        await message.answer(f"❌ Пользователь с Telegram ID {tg_id} не найден.")
        return

    # Найти подходящий тип испытания по размеру счёта
    ct_result = await session.execute(
        select(ChallengeType).where(
            ChallengeType.account_size == account_size,
            ChallengeType.is_active == True,
        ).limit(1)
    )
    ct = ct_result.scalar_one_or_none()
    if not ct:
        # Показать доступные
        available = await session.execute(
            select(ChallengeType.account_size, ChallengeType.name)
            .where(ChallengeType.is_active == True)
            .order_by(ChallengeType.account_size)
        )
        sizes = ", ".join([f"${int(row[0]):,} ({row[1]})" for row in available.all()])
        await message.answer(
            f"❌ Тип испытания на ${account_size:,.0f} не найден.\n"
            f"Доступные размеры: {sizes or 'нет активных типов'}",
            parse_mode="HTML",
        )
        return

    # Создать испытание без Bybit (manual mode)
    from datetime import datetime, timezone
    from decimal import Decimal

    now = datetime.now(timezone.utc)
    challenge = UserChallenge(
        user_id=user.id,
        challenge_type_id=ct.id,
        status=ChallengeStatus.phase1,
        phase=1,
        account_mode="demo",
        exchange="bybit",
        demo_account_id=f"MANUAL_{user.telegram_id}_{int(now.timestamp())}",
        demo_api_key_enc="",
        demo_api_secret_enc="",
        initial_balance=Decimal(str(account_size)),
        current_balance=Decimal(str(account_size)),
        peak_equity=Decimal(str(account_size)),
        daily_start_balance=Decimal(str(account_size)),
        daily_pnl=Decimal("0"),
        total_pnl=Decimal("0"),
        trading_days_count=0,
        started_at=now,
        daily_reset_at=now,
    )
    session.add(challenge)

    if user.role == UserRole.guest:
        user.role = UserRole.challenger

    await session.commit()

    uname = f"@{user.username}" if user.username else user.first_name
    logger.info(
        f"Admin {message.from_user.id} manually activated challenge #{challenge.id} "
        f"for user {tg_id} (${account_size:,.0f})"
    )

    await message.answer(
        f"✅ <b>Испытание активировано!</b>\n\n"
        f"👤 Трейдер: {uname} (<code>{tg_id}</code>)\n"
        f"💼 Challenge #{challenge.id}\n"
        f"💰 Счёт: <b>${account_size:,.0f}</b>\n"
        f"📋 Тип: {ct.name}\n"
        f"⚠️ <i>Создано вручную (без Bybit API). "
        f"Не забудьте привязать API-ключи через панель.</i>",
        parse_mode="HTML",
        reply_markup=_back_to_menu_kb(),
    )

    # Уведомить трейдера
    try:
        from app.services.notification_service import NotificationService
        notif = NotificationService(session)
        await notif.send_challenge_purchased(challenge)
    except Exception as e:
        logger.warning(f"Could not notify trader: {e}")


# ─── Inline Callbacks ──────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("adm:"))
async def handle_admin_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    if not _is_admin(callback.from_user.id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    data = callback.data  # e.g. "adm:stats", "adm:approve_payout:42"
    await callback.answer()

    parts = data.split(":")
    action = parts[1] if len(parts) > 1 else ""

    if action in ("menu", "refresh"):
        text = await _get_stats_text(session)
        try:
            await callback.message.edit_text(
                text, parse_mode="HTML", reply_markup=_main_menu_kb()
            )
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=_main_menu_kb())

    elif action == "stats":
        text = await _get_stats_text(session)
        await callback.message.answer(text, parse_mode="HTML", reply_markup=_back_to_menu_kb())

    elif action == "payouts":
        await _send_pending_payouts(callback.message, session)

    elif action == "users":
        await _send_user_list(callback.message, session)

    elif action == "activate_prompt":
        await callback.message.answer(
            "⚡ <b>Ручная активация испытания</b>\n\n"
            "Используйте команду:\n"
            "<code>/adm_activate &lt;telegram_id&gt; &lt;размер_счёта&gt;</code>\n\n"
            "Например:\n"
            "<code>/adm_activate 123456789 10000</code>\n\n"
            "Доступные размеры счетов: $5,000 · $10,000 · $25,000 · $50,000 · $100,000 · $200,000",
            parse_mode="HTML",
            reply_markup=_back_to_menu_kb(),
        )

    elif action == "approve_payout" and len(parts) > 2:
        payout_id = int(parts[2])
        result = await session.execute(
            select(Payout).where(Payout.id == payout_id, Payout.status == PayoutStatus.pending)
        )
        payout = result.scalar_one_or_none()
        if not payout:
            await callback.message.answer("❌ Выплата не найдена или уже обработана.")
            return

        payout.status = PayoutStatus.approved
        payout.processed_at = datetime.now(timezone.utc)
        await session.commit()

        # Уведомить трейдера
        try:
            from sqlalchemy.orm import selectinload
            ch_result = await session.execute(
                select(UserChallenge)
                .where(UserChallenge.id == payout.challenge_id)
                .options(selectinload(UserChallenge.user))
            )
            ch = ch_result.scalar_one_or_none()
            if ch:
                from app.services.notification_service import NotificationService
                notif = NotificationService(session)
                await notif.send_payout_approved(ch, payout.net_amount)
        except Exception as e:
            logger.warning(f"Payout notify error: {e}")

        await callback.message.answer(
            f"✅ <b>Выплата #{payout_id} одобрена</b>\n"
            f"💵 ${float(payout.amount):.2f} → {payout.network}\n"
            f"🏦 <code>{payout.wallet_address}</code>",
            parse_mode="HTML",
        )

    elif action == "reject_payout" and len(parts) > 2:
        payout_id = int(parts[2])
        result = await session.execute(
            select(Payout).where(Payout.id == payout_id, Payout.status == PayoutStatus.pending)
        )
        payout = result.scalar_one_or_none()
        if not payout:
            await callback.message.answer("❌ Выплата не найдена или уже обработана.")
            return

        payout.status = PayoutStatus.rejected
        payout.processed_at = datetime.now(timezone.utc)
        await session.commit()

        await callback.message.answer(
            f"❌ <b>Выплата #{payout_id} отклонена</b>\n"
            f"<i>Чтобы указать причину, используйте веб-панель.</i>",
            parse_mode="HTML",
        )
