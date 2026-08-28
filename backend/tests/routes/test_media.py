class FakeResponse:
    def __init__(self, content, content_type):
        self.content = content
        self.headers = {"content-type": content_type}


class FakeJellyfinClient:
    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error

    async def get(self, path):
        if self._error:
            raise self._error
        return self._response


async def test_poster_returns_404_when_jellyfin_not_configured(client):
    response = await client.get("/api/media/poster/abc123")
    assert response.status_code == 404


async def test_poster_streams_image_when_configured(client, db_session, monkeypatch):
    from app.core.security import encrypt_secret
    from app.db.models import Integration, ServiceName

    db_session.add(
        Integration(
            service=ServiceName.jellyfin,
            base_url="http://jellyfin:8096",
            api_key_encrypted=encrypt_secret("fake-key"),
            enabled=True,
        )
    )
    await db_session.commit()

    from app.integrations import service as integration_service

    fake_client = FakeJellyfinClient(response=FakeResponse(b"fake-image-bytes", "image/png"))
    monkeypatch.setattr(integration_service, "build_client", lambda integration: fake_client)

    response = await client.get("/api/media/poster/abc123")

    assert response.status_code == 200
    assert response.content == b"fake-image-bytes"
    assert response.headers["content-type"] == "image/png"


async def test_poster_returns_404_when_jellyfin_call_fails(client, db_session, monkeypatch):
    from app.core.security import encrypt_secret
    from app.db.models import Integration, ServiceName
    from app.integrations.base_client import IntegrationError

    db_session.add(
        Integration(
            service=ServiceName.jellyfin,
            base_url="http://jellyfin:8096",
            api_key_encrypted=encrypt_secret("fake-key"),
            enabled=True,
        )
    )
    await db_session.commit()

    from app.integrations import service as integration_service

    fake_client = FakeJellyfinClient(error=IntegrationError("Not found: /Items/abc123/Images/Primary"))
    monkeypatch.setattr(integration_service, "build_client", lambda integration: fake_client)

    response = await client.get("/api/media/poster/abc123")

    assert response.status_code == 404
