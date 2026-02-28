"""
Обработчики callback_query для инлайн-кнопок бота.
"""
from aiogram import Router
from aiogram.filters import Text
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main import get_main_menu_keyboard, get_open_app_keyboard
from app.models.user import User

router = Router(name="callbacks")


@router.callback_query(Text("cmd:balance"))
async def cb_balance(call: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    """Кнопка баланса — делегируем в handler команды."""
    from app.bot.handlers.commands import cmd_balance
    await call.answer()
    await cmd_balance(call.message, db_user, session)


@router.callback_query(Text("cmd:stats"))
async def cb_stats(call: CallbackQuery, db_user: User, session: AsyncSession) -> None:
    await call.answer()
    from app.bot.handlers.commands import cmd_stats
    await cmd_stats(call.message, db_user, session)


@router.callback_query(Text("cmd:achievements"))
async def cb_achievements(call: CallbackQuery, db_user: User) -> None:
    await call.answer()
    await call.message.answer(
        "🏅 Все достижения доступны в приложении CHM_KRYPTON.",
        reply_markup=get_open_app_keyboard("🏅 Открыть достижения"),
    )


@router.callback_query(Text("cmd:referral"))
async def cb_referral(call: CallbackQuery, db_user: User) -> None:
    await call.answer()
    from app.bot.handlers.commands import cmd_referral
    await cmd_referral(call.message, db_user)


@router.callback_query(Text("cmd:payout"))
async def cb_payout(call: CallbackQuery, db_user: User) -> None:
    await call.answer()
    from app.bot.handlers.commands import cmd_payout
    await cmd_payout(call.message, db_user)


@router.callback_query(Text("cmd:support"))
async def cb_support(call: CallbackQuery) -> None:
    await call.answer()
    from app.bot.handlers.commands import cmd_support
    await cmd_support(call.message)
