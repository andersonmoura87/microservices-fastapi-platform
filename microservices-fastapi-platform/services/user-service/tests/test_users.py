from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from app.database import get_session
from app.main import app
from httpx import ASGITransport, AsyncClient


async def _override_session():
    yield object()


app.dependency_overrides[get_session] = _override_session


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_health(client):
    async with client:
        r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_create_user_missing_fields(client):
    async with client:
        r = await client.post("/users", json={"name": "Test"})  # missing email
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_user_happy_path(client):
    fake = type(
        "U",
        (),
        {"id": 1, "name": "Ada", "email": "ada@example.com", "created_at": datetime(2026, 1, 1)},
    )()
    with patch("app.main.create_user", AsyncMock(return_value=fake)):
        async with client:
            r = await client.post("/users", json={"name": "Ada", "email": "ada@example.com"})
    assert r.status_code == 201
    assert r.json()["email"] == "ada@example.com"


@pytest.mark.asyncio
async def test_issue_token_for_existing_user(client):
    fake = type("U", (), {"id": 7, "email": "ada@example.com"})()
    with patch("app.main.get_user_by_email", AsyncMock(return_value=fake)):
        async with client:
            r = await client.post("/auth/token", json={"email": "ada@example.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


@pytest.mark.asyncio
async def test_issue_token_unknown_user(client):
    with patch("app.main.get_user_by_email", AsyncMock(return_value=None)):
        async with client:
            r = await client.post("/auth/token", json={"email": "nope@example.com"})
    assert r.status_code == 404
