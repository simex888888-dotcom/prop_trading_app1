# 📈 Prop Trading Telegram Mini App

Полноценное prop trading приложение для криптовалют внутри Telegram.

## Стек
- **Frontend:** React + Vite + Framer Motion + @twa-dev/sdk
- **Backend:** Python + FastAPI + aiogram 3.x
- **БД:** PostgreSQL + Redis
- **Деплой:** Docker Compose / systemd

## Быстрый старт

```bash
# Клонируй репозиторий
git clone <repo>
cd prop_trading_app

# Настрой переменные окружения
cp .env.example .env
cp backend/.env.example backend/.env
# Заполни BOT_TOKEN и другие значения

# Запусти через Docker Compose
docker compose up -d --build

# Проверь
curl http://localhost:8000/health
```

## Документация
Смотри [DEPLOY.md](./DEPLOY.md) для полной инструкции по деплою.

## Функциональность
- ✅ Авторизация через Telegram initData (HMAC-SHA256)
- ✅ 3 фазы: Evaluation → Verification → Funded
- ✅ Реальные цены с Binance (REST + WebSocket)
- ✅ Автоматическое закрытие по TP/SL
- ✅ Контроль дневной и trailing просадки
- ✅ Калькулятор риска (% от депозита → размер позиции)
- ✅ Leaderboard с кэшированием в Redis
- ✅ Telegram-уведомления через бота
- ✅ Тёмная/светлая тема
- ✅ Framer Motion анимации
