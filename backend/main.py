import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import close_redis, engine, get_redis
from routers import auth, trading, account, leaderboard
from services.price_feed import price_feed_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Prop Trading API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "https://web.telegram.org,https://k.web.telegram.org,http://localhost:5173,http://localhost:4173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(trading.router, prefix="/api/v1")
app.include_router(account.router, prefix="/api/v1")
app.include_router(leaderboard.router, prefix="/api/v1")


@app.on_event("startup")
async def startup():
    logger.info("Starting up...")
    # Запускаем WebSocket фид цен
    await price_feed_manager.start()
    logger.info("Price feed started")

    # Проверяем Redis
    redis = await get_redis()
    await redis.ping()
    logger.info("Redis connected")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down...")
    await price_feed_manager.stop()
    await close_redis()
    await engine.dispose()
    logger.info("Cleanup complete")


@app.get("/health")
async def health_check():
    redis = await get_redis()
    await redis.ping()
    return {"status": "ok", "service": "prop-trading-api"}
