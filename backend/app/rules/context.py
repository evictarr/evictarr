from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ServiceName
from app.integrations import service as integration_service
from app.integrations.base_client import IntegrationError


class RuleContext:
    """Lazily builds and caches one integration client per service for the
    lifetime of a single scan run, so each handler only pays for the
    services it actually needs."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._clients: dict[ServiceName, object] = {}
        self._jellyfin_user_id: str | None = None

    async def client(self, service: ServiceName):
        if service not in self._clients:
            integration = await integration_service.get_integration(self.db, service)
            if integration is None or not integration.enabled:
                raise IntegrationError(f"{service.value} is not enabled in Settings")
            self._clients[service] = integration_service.build_client(integration)
        return self._clients[service]

    async def jellyfin_user_id(self) -> str:
        if self._jellyfin_user_id is None:
            integration = await integration_service.get_integration(self.db, ServiceName.jellyfin)
            user_id = (integration.extra_config or {}).get("jellyfin_user_id") if integration else None
            if not user_id:
                raise IntegrationError("Jellyfin user to track is not selected in Settings")
            self._jellyfin_user_id = user_id
        return self._jellyfin_user_id
