from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret, encrypt_secret
from app.db.models import Integration, ServiceName, TestStatus
from app.integrations.base_client import IntegrationError
from app.integrations.jellyfin_client import JellyfinClient
from app.integrations.radarr_client import RadarrClient
from app.integrations.seerr_client import SeerrClient
from app.integrations.sonarr_client import SonarrClient

_CLIENTS = {
    ServiceName.jellyfin: JellyfinClient,
    ServiceName.seerr: SeerrClient,
    ServiceName.radarr: RadarrClient,
    ServiceName.sonarr: SonarrClient,
}


async def get_integration(db: AsyncSession, service: ServiceName) -> Integration | None:
    result = await db.execute(select(Integration).where(Integration.service == service))
    return result.scalar_one_or_none()


async def list_integrations(db: AsyncSession) -> list[Integration]:
    result = await db.execute(select(Integration))
    return list(result.scalars().all())


async def update_integration(
    db: AsyncSession,
    service: ServiceName,
    base_url: str | None,
    api_key: str | None,
    extra_config: dict | None,
    enabled: bool,
) -> Integration:
    integration = await get_integration(db, service)
    if integration is None:
        raise ValueError(f"Unknown service {service}")
    integration.base_url = base_url
    if api_key:
        integration.api_key_encrypted = encrypt_secret(api_key)
    integration.extra_config = extra_config or {}
    integration.enabled = enabled
    await db.commit()
    return integration


def build_client(integration: Integration):
    if not integration.base_url or not integration.api_key_encrypted:
        raise IntegrationError("Base URL and API key must be configured first")
    client_cls = _CLIENTS[integration.service]
    api_key = decrypt_secret(integration.api_key_encrypted)
    return client_cls(integration.base_url, api_key)


async def test_integration(db: AsyncSession, service: ServiceName) -> tuple[bool, str]:
    integration = await get_integration(db, service)
    if integration is None:
        raise ValueError(f"Unknown service {service}")

    try:
        client = build_client(integration)
        detail = await client.test_connection()
        ok = True
    except IntegrationError as exc:
        detail = str(exc)
        ok = False

    integration.last_test_status = TestStatus.ok if ok else TestStatus.failed
    integration.last_test_at = datetime.now(timezone.utc)
    integration.last_test_detail = detail
    await db.commit()
    return ok, detail
