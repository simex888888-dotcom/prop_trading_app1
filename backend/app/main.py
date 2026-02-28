"""
CHM_KRYPTON — FastAPI Application Entry Point
"""
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.core.config import settings
from app.core.database import close_db, get_db, get_redis
from app.tasks.scheduler import setup_scheduler

# ─── Логирование ──────────────────────────────────────────────────────────────
logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG" if settings.app_debug else "INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)
logger.add(
    "logs/app.log",
    rotation="100 MB",
    retention="30 days",
    level="INFO",
    compression="gz",
)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Запуск и остановка сервисов."""
    logger.info(f"Starting CHM_KRYPTON v{settings.app_version} in {settings.app_env} mode")

    # Проверка Redis
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")

    # Запуск APScheduler
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("APScheduler started")

    yield

    # Graceful shutdown
    logger.info("Shutting down CHM_KRYPTON...")
    scheduler.shutdown(wait=True)
    await close_db()
    logger.info("Shutdown complete")


# ─── FastAPI App ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="CHM_KRYPTON API",
    description="Крипто проп-трейдинг платформа — Trade Like an Element",
    version=settings.app_version,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global Exception Handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"},
    )


# ─── Роутеры ──────────────────────────────────────────────────────────────────

from app.api.routes import (
    achievements,
    admin,
    auth,
    challenges,
    leaderboard,
    payouts,
    referral,
    stats,
    trading,
)

API_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(challenges.router, prefix=API_PREFIX)
app.include_router(trading.router, prefix=API_PREFIX)
app.include_router(stats.router, prefix=API_PREFIX)
app.include_router(payouts.router, prefix=API_PREFIX)
app.include_router(achievements.router, prefix=API_PREFIX)
app.include_router(leaderboard.router, prefix=API_PREFIX)
app.include_router(referral.router, prefix=API_PREFIX)
app.include_router(admin.router, prefix=API_PREFIX)


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health_check() -> dict:
    redis = await get_redis()
    await redis.ping()
    return {
        "status": "ok",
        "service": "chm-krypton",
        "version": settings.app_version,
        "env": settings.app_env,
    }
