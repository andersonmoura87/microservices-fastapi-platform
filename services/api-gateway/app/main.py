import time
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as redis
import structlog
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from .config import settings
from .logging_config import configure_logging
from .ratelimit import RateLimiter
from .tracing import setup_tracing

configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Reuse one pooled client/connection for the process lifetime instead of
    # building a new one per request, and tear them down cleanly on SIGTERM.
    app.state.http = httpx.AsyncClient(timeout=settings.upstream_timeout)
    app.state.redis = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.limiter = RateLimiter(app.state.redis)
    logger.info("gateway.startup")
    try:
        yield
    finally:
        logger.info("gateway.shutdown")
        await app.state.http.aclose()
        await app.state.redis.aclose()


app = FastAPI(
    title="API Gateway",
    description="Unified entry point for the microservices platform",
    version="1.0.0",
    lifespan=lifespan,
)
setup_tracing(app, "api-gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

REQUEST_COUNT = Counter(
    "gateway_requests_total",
    "Total requests through gateway",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "gateway_request_duration_seconds",
    "Request latency in seconds",
    ["method", "path"],
)
RATE_LIMITED = Counter("gateway_rate_limited_total", "Requests rejected by the rate limiter")

# Hop-by-hop headers must not be forwarded to upstreams.
_STRIP_HEADERS = {"host", "content-length", "connection", "keep-alive", "transfer-encoding"}
_UNLIMITED_PATHS = {"/health", "/metrics"}


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(
        time.perf_counter() - start
    )
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    return response


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if settings.rate_limit_enabled and request.url.path not in _UNLIMITED_PATHS:
        identity = request.client.host if request.client else "unknown"
        allowed, retry_after = await request.app.state.limiter.hit(identity)
        if not allowed:
            RATE_LIMITED.inc()
            logger.info("gateway.rate_limited", identity=identity)
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


async def _proxy(request: Request, url: str) -> Response:
    body = await request.body()
    headers = {k: v for k, v in request.headers.items() if k.lower() not in _STRIP_HEADERS}
    client: httpx.AsyncClient = request.app.state.http
    try:
        upstream = await client.request(
            request.method, url, content=body, headers=headers, params=request.query_params
        )
    except httpx.ConnectError as exc:
        logger.error("gateway.upstream_unreachable", url=url, error=str(exc))
        raise HTTPException(
            status_code=503, detail="Upstream service unavailable"
        ) from exc
    except httpx.TimeoutException as exc:
        logger.error("gateway.upstream_timeout", url=url)
        raise HTTPException(
            status_code=504, detail="Upstream service timed out"
        ) from exc
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type"),
    )


@app.get("/health", tags=["platform"])
async def health(request: Request):
    results = {}
    client: httpx.AsyncClient = request.app.state.http
    for name, base in (
        ("user-service", settings.user_service_url),
        ("data-service", settings.data_service_url),
    ):
        try:
            r = await client.get(f"{base}/health", timeout=5.0)
            results[name] = "healthy" if r.status_code == 200 else "degraded"
        except httpx.HTTPError:
            results[name] = "unreachable"
    overall = "healthy" if all(v == "healthy" for v in results.values()) else "degraded"
    return {"status": overall, "services": results}


@app.get("/metrics", tags=["platform"], include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.api_route("/users/{path:path}", methods=["GET", "PUT", "DELETE"], tags=["users"])
async def proxy_users(path: str, request: Request):
    return await _proxy(request, f"{settings.user_service_url}/users/{path}")


@app.post("/users", tags=["users"])
async def create_user(request: Request):
    return await _proxy(request, f"{settings.user_service_url}/users")


@app.api_route("/auth/{path:path}", methods=["POST"], tags=["auth"])
async def proxy_auth(path: str, request: Request):
    return await _proxy(request, f"{settings.user_service_url}/auth/{path}")


@app.post("/data/ingest", tags=["data"])
async def ingest_data(request: Request):
    return await _proxy(request, f"{settings.data_service_url}/data/ingest")


@app.api_route("/data/{path:path}", methods=["GET", "DELETE"], tags=["data"])
async def proxy_data(path: str, request: Request):
    return await _proxy(request, f"{settings.data_service_url}/data/{path}")
