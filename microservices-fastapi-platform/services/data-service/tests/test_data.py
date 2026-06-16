from unittest.mock import AsyncMock, patch

import pytest
from app.database import get_session
from app.main import app
from httpx import ASGITransport, AsyncClient


class _FakeSession:
    async def execute(self, *_args, **_kwargs):
        return None


async def _override_session():
    yield _FakeSession()


app.dependency_overrides[get_session] = _override_session


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health_reports_dependency_status(client):
    with patch("app.main.cache.get_client") as get_client:
        get_client.return_value.ping = AsyncMock(return_value=True)
        async with client:
            r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "data-service"
    assert body["checks"]["database"] == "healthy"


@pytest.mark.asyncio
async def test_ingest_rejects_invalid_payload(client):
    async with client:
        r = await client.post("/data/ingest", json={"key": "k"})  # missing payload
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_records_served_from_cache(client):
    cached = [{"id": 1, "key": "k", "payload": {"a": 1}, "created_at": "2026-01-01T00:00:00"}]
    with patch("app.main.cache.get_json", AsyncMock(return_value=cached)):
        async with client:
            r = await client.get("/data/records")
    assert r.status_code == 200
    assert r.json() == cached
