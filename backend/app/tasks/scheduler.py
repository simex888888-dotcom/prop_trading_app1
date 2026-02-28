"""
APScheduler задачи для CHM_KRYPTON.
"""
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.core.config import settings
from app.core.database import get_db

scheduler = AsyncIOScheduler(timezone="UTC")


async def _run_challenge_engine() -> None:
    """Запускает ChallengeEngine для всех активных испытаний."""
    from app.services.challenge_engine import ChallengeEngine
    async for session in get_db():
        try:
            engine = ChallengeEngine(session)
            await engine.run_all_checks()
        except Exception as e:
            logger.error(f"ChallengeEngine task error: {e}", exc_info=True)


async def _check_master_balance() -> None:
    """Проверяет баланс master аккаунта Bybit. Раз в час."""
    from app.services.exchange.bybit_master import BybitMasterClient
    from app.services.notification_service import NotificationService

    client = BybitMasterClient()
    try:
        ok = await client.check_master_balance()
        if not ok:
            async for session in get_db():
                svc = NotificationService(session)
                await svc.send_to_super_admin(
                    "🚨 <b>Внимание!</b> Баланс master-аккаунта Bybit ниже минимального порога! "
                    "Пополните кошелёк для выдачи funded аккаунтов."
                )
                break
    except Exception as e:
        logger.error(f"Master balance check failed: {e}")
    finally:
        await client.close()


async def _pay_referral_bonuses() -> None:
    """Выплачивает реферальные бонусы (раз в 7 дней)."""
    from app.services.referral_service import ReferralService
    async for session in get_db():
        try:
            svc = ReferralService(session)
            await svc.process_weekly_payouts()
        except Exception as e:
            logger.error(f"Referral payout task error: {e}", exc_info=True)
        break


async def _update_leaderboards() -> None:
    """Обновляет кеш лидербордов. Каждые 5 минут."""
    from app.services.leaderboard_service import LeaderboardService
    async for session in get_db():
        try:
            svc = LeaderboardService(session)
            await svc.rebuild_cache()
        except Exception as e:
            logger.error(f"Leaderboard update error: {e}", exc_info=True)
        break


async def _update_achievements() -> None:
    """Проверяет и выдаёт новые достижения. Каждые 5 минут."""
    from app.services.achievement_service import AchievementService
    async for session in get_db():
        try:
            svc = AchievementService(session)
            await svc.check_all_users()
        except Exception as e:
            logger.error(f"Achievement check error: {e}", exc_info=True)
        break


def setup_scheduler() -> AsyncIOScheduler:
    """Настраивает и возвращает планировщик."""
    # ChallengeEngine каждые 30 секунд
    scheduler.add_job(
        _run_challenge_engine,
        trigger=IntervalTrigger(seconds=settings.engine_check_interval_seconds),
        id="challenge_engine",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Проверка баланса master каждый час
    scheduler.add_job(
        _check_master_balance,
        trigger=IntervalTrigger(hours=1),
        id="master_balance_check",
        replace_existing=True,
        max_instances=1,
    )

    # Реферальные выплаты каждые 7 дней (по понедельникам в 00:00 UTC)
    scheduler.add_job(
        _pay_referral_bonuses,
        trigger=CronTrigger(day_of_week="mon", hour=0, minute=0),
        id="referral_payouts",
        replace_existing=True,
        max_instances=1,
    )

    # Обновление лидербордов каждые 5 минут
    scheduler.add_job(
        _update_leaderboards,
        trigger=IntervalTrigger(minutes=5),
        id="leaderboard_update",
        replace_existing=True,
        max_instances=1,
    )

    # Проверка достижений каждые 5 минут
    scheduler.add_job(
        _update_achievements,
        trigger=IntervalTrigger(minutes=5),
        id="achievement_check",
        replace_existing=True,
        max_instances=1,
    )

    logger.info("APScheduler configured with all tasks")
    return scheduler
