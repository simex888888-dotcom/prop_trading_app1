"""
/achievements — достижения и прогресс пользователя.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.models.achievement import Achievement, UserAchievement
from app.models.user import User
from app.schemas.common import APIResponse

router = APIRouter(prefix="/achievements", tags=["achievements"])


class AchievementOut(BaseModel):
    id: int
    key: str
    name: str
    description: str
    lottie_file: Optional[str]
    levels_config: dict
    # Прогресс пользователя
    level: str
    progress: float
    unlocked_at: Optional[datetime]

    model_config = {"from_attributes": True}


@router.get("", response_model=APIResponse[list[AchievementOut]])
async def get_all_achievements(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[AchievementOut]]:
    """Все достижения с прогрессом текущего пользователя."""
    # Все достижения
    achievements_result = await session.execute(select(Achievement))
    achievements = achievements_result.scalars().all()

    # Достижения пользователя
    user_ach_result = await session.execute(
        select(UserAchievement).where(UserAchievement.user_id == user.id)
    )
    user_achievements = {ua.achievement_id: ua for ua in user_ach_result.scalars().all()}

    result = []
    for ach in achievements:
        ua = user_achievements.get(ach.id)
        result.append(AchievementOut(
            id=ach.id,
            key=ach.key,
            name=ach.name_ru,
            description=ach.description_ru,
            lottie_file=ach.lottie_file,
            levels_config=ach.levels_config,
            level=ua.level if ua else "locked",
            progress=float(ua.progress) if ua else 0.0,
            unlocked_at=ua.unlocked_at if ua else None,
        ))
    return APIResponse(data=result)


@router.get("/unlocked", response_model=APIResponse[list[AchievementOut]])
async def get_unlocked_achievements(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> APIResponse[list[AchievementOut]]:
    """Только разблокированные достижения."""
    result = await session.execute(
        select(UserAchievement, Achievement)
        .join(Achievement, UserAchievement.achievement_id == Achievement.id)
        .where(
            UserAchievement.user_id == user.id,
            UserAchievement.level != "locked",
        )
        .order_by(UserAchievement.unlocked_at.desc())
    )
    rows = result.all()

    return APIResponse(data=[
        AchievementOut(
            id=ach.id,
            key=ach.key,
            name=ach.name_ru,
            description=ach.description_ru,
            lottie_file=ach.lottie_file,
            levels_config=ach.levels_config,
            level=ua.level,
            progress=float(ua.progress),
            unlocked_at=ua.unlocked_at,
        )
        for ua, ach in rows
    ])
