"""Клавиатуры Telegram бота CHM_KRYPTON."""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)

from app.core.config import settings


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота с кнопкой открытия Mini App."""
    webapp_url = settings.telegram_webapp_url
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Открыть CHM_KRYPTON",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ],
            [
                InlineKeyboardButton(text="💰 Баланс", callback_data="cmd:balance"),
                InlineKeyboardButton(text="📈 Статистика", callback_data="cmd:stats"),
            ],
            [
                InlineKeyboardButton(text="🏆 Достижения", callback_data="cmd:achievements"),
                InlineKeyboardButton(text="👥 Рефералы", callback_data="cmd:referral"),
            ],
            [
                InlineKeyboardButton(text="💳 Выплата", callback_data="cmd:payout"),
                InlineKeyboardButton(text="❓ Поддержка", callback_data="cmd:support"),
            ],
        ]
    )


def get_open_app_keyboard(text: str = "📱 Открыть приложение") -> InlineKeyboardMarkup:
    """Кнопка открытия Mini App."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text=text,
                web_app=WebAppInfo(url=settings.telegram_webapp_url),
            )
        ]]
    )


def get_support_keyboard() -> InlineKeyboardMarkup:
    """Кнопка связи с поддержкой."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="💬 Написать в поддержку",
                url="https://t.me/chm_krypton_support",
            ),
            InlineKeyboardButton(
                text="📱 Открыть приложение",
                web_app=WebAppInfo(url=settings.telegram_webapp_url),
            ),
        ]]
    )
