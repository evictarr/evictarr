from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSettings


async def ensure_app_settings(db: AsyncSession) -> None:
    result = await db.execute(select(AppSettings).where(AppSettings.id == 1))
    if result.scalar_one_or_none() is not None:
        return
    db.add(AppSettings(id=1))
    await db.commit()
