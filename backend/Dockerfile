FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs

EXPOSE 8000

CMD ["sh", "-c", "set -e; echo '>>> [1/3] prestart...'; python prestart.py; echo '>>> [2/3] alembic...'; alembic upgrade head; echo '>>> [3/3] starting uvicorn on port '${PORT:-8000}'...'; exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info"]
