import httpx
import pytest
from app.main import app
from httpx import ASGITransport, AsyncClient


class _FakeResponse:
    def __init__(self, status_code=200, content=b"{}", content_type="application/json"):
        self.status_code = status_code
        self.content = content
        self.headers = {"content-type": content_type}


class _FakeHttp:
    """Stand-in for the pooled httpx client kept on app.state."""

    def __init__(self, *, get=None, request=None, raises=None):
        self._get = get
        self._request = request
        self._raises = raises

    async def get(self, *_args, **_kwargs):
        if self._raises:
            raise self._raises
        return self._get

    async def request(self, *_args, **_kwargs):
        if self._raises:
            raise self._raises
        return self._request


class _AllowLimiter:
    async def hit(self, _identity):
        return True, 0


class _DenyLimiter:
    async def hit(self, _identity):
        return False, 42


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _wire(http, limiter=None):
    # Lifespan doesn't run under ASGITransport, so seed app.state ourselves.
    app.state.http = http
    app.state.limiter = limiter or _AllowLimiter()


@pytest.mark.asyncio
async def test_health_aggregates_healthy(client):
    _wire(_FakeHttp(get=_FakeResponse(200)))
    async with client:
        r = await client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["services"] == {"user-service": "healthy", "data-service": "healthy"}


@pytest.mark.asyncio
async def test_proxy_forwards_upstream_response(client):
    _wire(_FakeHttp(request=_FakeResponse(status_code=201, content=b'{"id": 1}')))
    async with client:
        r = await client.post("/users", json={"name": "Ada", "email": "ada@example.com"})
    assert r.status_code == 201
    assert r.json() == {"id": 1}


@pytest.mark.asyncio
async def test_proxy_returns_503_when_upstream_unreachable(client):
    _wire(_FakeHttp(raises=httpx.ConnectError("boom")))
    async with client:
        r = await client.get("/data/records")
    assert r.status_code == 503


@pytest.mark.asyncio
async def test_rate_limit_returns_429(client):
    _wire(_FakeHttp(request=_FakeResponse()), limiter=_DenyLimiter())
    async with client:
        r = await client.get("/data/records")
    assert r.status_code == 429
    assert r.headers["Retry-After"] == "42"
