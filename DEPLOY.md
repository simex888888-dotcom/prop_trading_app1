# 🚀 Инструкция по деплою Prop Trading Mini App

## Предварительные требования
- Docker + Docker Compose (для продакшн)
- Python 3.12+, Node.js 20+ (для локальной разработки)
- Зарегистрированный Telegram бот через @BotFather
- VPS/сервер с публичным IP и доменом (для продакшн)

---

## 📱 1. Создание бота в Telegram

```bash
# 1. Открой @BotFather в Telegram
# 2. /newbot — создай бота, получи BOT_TOKEN
# 3. /newapp — создай Mini App:
#    - Выбери бота
#    - Название: Prop Trading
#    - URL: https://your-domain.com  (после деплоя)
#    - Short name: app (будет использоваться в ссылке t.me/your_bot/app)
```

---

## 💻 2. Локальная разработка

### Backend
```bash
cd prop_trading_app/backend

# Создай виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Установи зависимости
pip install -r requirements.txt

# Скопируй и настрой .env
cp .env.example .env
# Отредактируй .env — вставь BOT_TOKEN и настрой DB/Redis

# Запусти PostgreSQL и Redis (через Docker)
docker run -d --name pg -e POSTGRES_DB=prop_trading -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password -p 5432:5432 postgres:16-alpine

docker run -d --name redis -p 6379:6379 redis:7-alpine

# Применяй миграции
alembic upgrade head

# Запусти FastAPI
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# В отдельном терминале — запусти бота
python bot.py
```

### Frontend
```bash
cd prop_trading_app/frontend

# Установи зависимости
npm install

# Скопируй и настрой .env
cp .env.example .env
# Для локальной разработки:
# VITE_API_URL=/api/v1  (vite proxy перенаправляет на localhost:8000)

# Запусти dev-сервер
npm run dev
# Приложение доступно на http://localhost:5173
```

### Тестирование Mini App локально
Telegram Mini App требует HTTPS. Для локального тестирования используй ngrok:

```bash
# Установи ngrok: https://ngrok.com/download
ngrok http 5173

# Скопируй HTTPS URL (например https://abc123.ngrok-free.app)
# В @BotFather → /setmenubutton → вставь этот URL
# Открой бота в Telegram и нажми Menu
```

---

## 🐳 3. Деплой через Docker Compose (рекомендуется)

### 3.1 Подготовка сервера

```bash
# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Устанавливаем Docker Compose
sudo apt install docker-compose-plugin -y

# Устанавливаем certbot для SSL
sudo apt install certbot -y
```

### 3.2 SSL сертификат

```bash
# Получаем сертификат (замени your-domain.com на свой домен)
sudo certbot certonly --standalone -d your-domain.com

# Копируем сертификаты
mkdir -p prop_trading_app/ssl
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem prop_trading_app/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem prop_trading_app/ssl/
sudo chown $USER:$USER prop_trading_app/ssl/*.pem
```

### 3.3 Настройка конфигурации

```bash
cd prop_trading_app

# Создаём .env для docker-compose
cat > .env << EOF
POSTGRES_PASSWORD=your_very_secure_password
VITE_API_URL=https://your-domain.com/api/v1
EOF

# Создаём backend/.env
cat > backend/.env << EOF
BOT_TOKEN=your_bot_token_from_botfather
MINI_APP_URL=https://t.me/your_bot/app
DATABASE_URL=postgresql+asyncpg://postgres:your_very_secure_password@postgres:5432/prop_trading
REDIS_URL=redis://redis:6379/0
ALLOWED_ORIGINS=https://web.telegram.org,https://k.web.telegram.org,https://your-domain.com
EOF

# Обновляем nginx.conf — заменяем your-domain.com на свой домен
sed -i 's/your-domain.com/actual-domain.com/g' nginx.conf
```

### 3.4 Запуск

```bash
# Строим и запускаем все контейнеры
docker compose up -d --build

# Проверяем статус
docker compose ps

# Смотрим логи
docker compose logs -f backend
docker compose logs -f bot
docker compose logs -f frontend

# Проверяем health
curl https://your-domain.com/api/v1/health
```

### 3.5 Обновление приложения

```bash
cd prop_trading_app

# Получаем новый код
git pull

# Пересобираем и перезапускаем
docker compose up -d --build

# Миграции применятся автоматически при старте backend
```

---

## ⚙️ 4. Деплой через systemd (альтернатива)

### 4.1 Установка зависимостей

```bash
# PostgreSQL
sudo apt install postgresql postgresql-contrib -y
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Создаём БД
sudo -u postgres psql -c "CREATE DATABASE prop_trading;"
sudo -u postgres psql -c "CREATE USER propuser WITH PASSWORD 'securepass';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE prop_trading TO propuser;"

# Redis
sudo apt install redis-server -y
sudo systemctl start redis
sudo systemctl enable redis

# Python
sudo apt install python3.12 python3.12-venv -y

# Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install nodejs -y

# Nginx
sudo apt install nginx -y
```

### 4.2 Деплой backend

```bash
cd /opt
sudo git clone https://your-repo-url.git prop_trading_app
sudo chown -R $USER:$USER /opt/prop_trading_app

cd /opt/prop_trading_app/backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Настраиваем .env
cp .env.example .env
nano .env  # Заполняем все значения

# Применяем миграции
alembic upgrade head

# Строим frontend
cd /opt/prop_trading_app/frontend
npm ci
VITE_API_URL=/api/v1 npm run build
```

### 4.3 Systemd unit для FastAPI

```bash
sudo tee /etc/systemd/system/prop-trading-api.service << EOF
[Unit]
Description=Prop Trading FastAPI
After=network.target postgresql.service redis.service

[Service]
Type=exec
User=$USER
WorkingDirectory=/opt/prop_trading_app/backend
Environment="PATH=/opt/prop_trading_app/backend/venv/bin"
EnvironmentFile=/opt/prop_trading_app/backend/.env
ExecStart=/opt/prop_trading_app/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000 --workers 2 --loop uvloop
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

### 4.4 Systemd unit для бота

```bash
sudo tee /etc/systemd/system/prop-trading-bot.service << EOF
[Unit]
Description=Prop Trading Telegram Bot
After=network.target postgresql.service redis.service prop-trading-api.service

[Service]
Type=exec
User=$USER
WorkingDirectory=/opt/prop_trading_app/backend
Environment="PATH=/opt/prop_trading_app/backend/venv/bin"
EnvironmentFile=/opt/prop_trading_app/backend/.env
ExecStart=/opt/prop_trading_app/backend/venv/bin/python bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

### 4.5 Запуск сервисов

```bash
sudo systemctl daemon-reload
sudo systemctl enable prop-trading-api prop-trading-bot
sudo systemctl start prop-trading-api prop-trading-bot

# Проверка
sudo systemctl status prop-trading-api
sudo journalctl -u prop-trading-api -f
```

### 4.6 Nginx для systemd деплоя

```bash
# Копируем собранный frontend
sudo cp -r /opt/prop_trading_app/frontend/dist /var/www/prop_trading

# Создаём nginx конфиг
sudo cp /opt/prop_trading_app/nginx.conf /etc/nginx/sites-available/prop_trading
sudo sed -i 's|/usr/share/nginx/html|/var/www/prop_trading|g' /etc/nginx/sites-available/prop_trading
sudo ln -s /etc/nginx/sites-available/prop_trading /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 🔧 5. Настройка бота в BotFather

```
1. /setmenubutton — установить кнопку меню:
   - Выбери бота
   - Button Text: 📈 Prop Trading
   - URL: https://your-domain.com

2. /setdomain — разрешить домен для Web App:
   - your-domain.com

3. После настройки /start в боте должна открываться Mini App
```

---

## 🔄 6. Автообновление SSL

```bash
# Добавляем cron для автообновления certbot
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet && docker compose -f /opt/prop_trading_app/docker-compose.yml restart frontend") | crontab -
```

---

## 📊 7. Мониторинг

```bash
# Логи в Docker
docker compose logs -f --tail=100

# Логи в systemd
journalctl -u prop-trading-api -f --since "1 hour ago"

# Метрики PostgreSQL
docker compose exec postgres psql -U postgres -d prop_trading -c "
  SELECT schemaname, tablename, n_live_tup, n_dead_tup
  FROM pg_stat_user_tables ORDER BY n_live_tup DESC;
"

# Redis memory
docker compose exec redis redis-cli info memory | grep used_memory_human
```

---

## ❓ Частые проблемы

**Ошибка CORS:** Проверь ALLOWED_ORIGINS в backend/.env — должен содержать домен фронтенда и web.telegram.org

**initData invalid:** Убедись, что BOT_TOKEN совпадает с тем, от которого открывается Mini App. В dev-режиме без Telegram авторизация пропускается.

**WebSocket цен не работает:** Binance может блокировать с некоторых IP. Попробуй добавить proxy или использовать только REST (price_feed.py).

**База не создаётся:** Проверь DATABASE_URL и права пользователя PostgreSQL.
