import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import LibraryContext, OrphanedFile, ServiceName
from app.integrations import service as integration_service
from app.integrations.base_client import IntegrationError

logger = logging.getLogger(__name__)

_MEDIA_EXTENSIONS = {".mkv", ".mp4", ".avi", ".m4v", ".mov", ".wmv", ".ts"}


async def _tracked_paths(db: AsyncSession, service: ServiceName) -> set[str] | None:
    integration = await integration_service.get_integration(db, service)
    if integration is None or not integration.enabled:
        return None
    try:
        client = integration_service.build_client(integration)
        return await client.get_tracked_file_paths()
    except IntegrationError:
        logger.exception("Could not fetch tracked paths from %s for orphaned-file scan", service.value)
        return None


async def _scan_library(db: AsyncSession, mount_path: str, context: LibraryContext, tracked: set[str]) -> int:
    root = Path(mount_path)
    if not root.is_dir():
        logger.warning(
            "Orphaned-file scan skipped for %s: %s is not a mounted directory "
            "(check MOVIES_LIBRARY_PATH/TV_LIBRARY_PATH against your volume mounts)",
            context.value,
            mount_path,
        )
        return 0

    tracked_normalized = {str(Path(p)) for p in tracked}
    found = 0
    for file_path in root.rglob("*"):
        if not file_path.is_file() or file_path.suffix.lower() not in _MEDIA_EXTENSIONS:
            continue
        normalized = str(file_path)
        if normalized in tracked_normalized:
            continue

        existing = await db.execute(select(OrphanedFile).where(OrphanedFile.path == normalized))
        if existing.scalar_one_or_none() is not None:
            continue

        db.add(
            OrphanedFile(
                path=normalized,
                size_bytes=file_path.stat().st_size,
                service_context=context,
            )
        )
        found += 1

    if found:
        await db.commit()
    return found


async def run_scan(db: AsyncSession) -> int:
    settings = get_settings()
    total = 0

    radarr_tracked = await _tracked_paths(db, ServiceName.radarr)
    if radarr_tracked is not None:
        total += await _scan_library(db, settings.movies_library_path, LibraryContext.movies, radarr_tracked)

    sonarr_tracked = await _tracked_paths(db, ServiceName.sonarr)
    if sonarr_tracked is not None:
        total += await _scan_library(db, settings.tv_library_path, LibraryContext.tv, sonarr_tracked)

    return total
