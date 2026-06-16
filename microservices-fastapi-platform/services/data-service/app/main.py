import time

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from . import cache, crud
from .config import settings
from .database import get_session
from .logging_config import configure_logging
from .schemas import RecordCreate, RecordOut

configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)

app = FastAPI(title="Data Service", version="1.0.0")

REQUEST_COUNT = Counter(
    "data_requests_total", "Total requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "data_request_duration_seconds", "Request latency in seconds", ["method", "path"]
)
CACHE_HITS = Counter("data_cache_hits_total", "Cache hits")
CACHE_MISSES = Counter("data_cache_misses_total", "Cache misses")


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(
        time.perf_counter() - start
    )
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    return response


@app.get("/health")
async def health(session: AsyncSession = Depends(get_session)):
    checks = {"database": "healthy", "cache": "healthy"}
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:  # surfaced as degraded, not a crash
        logger.error("health.db_unreachable", error=str(exc))
        checks["database"] = "unreachable"
    try:
        await cache.get_client().ping()
    except Exception as exc:
        logger.error("health.cache_unreachable", error=str(exc))
        checks["cache"] = "unreachable"

    status = "healthy" if all(v == "healthy" for v in checks.values()) else "degraded"
    return {"status": status, "service": "data-service", "checks": checks}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/data/ingest", response_model=RecordOut, status_code=201)
async def ingest(payload: RecordCreate, session: AsyncSession = Depends(get_session)):
    record = await crud.create_record(session, payload)
    # New write makes any cached listing stale.
    await cache.delete(cache.key("records"))
    logger.info("record.ingested", record_id=record.id, key=record.key)
    return record


@app.get("/data/records", response_model=list[RecordOut])
async def list_records(session: AsyncSession = Depends(get_session)):
    cache_key = cache.key("records")
    cached = await cache.get_json(cache_key)
    if cached is not None:
        CACHE_HITS.inc()
        return cached

    CACHE_MISSES.inc()
    records = await crud.list_records(session)
    serialised = [RecordOut.model_validate(r).model_dump() for r in records]
    await cache.set_json(cache_key, serialised)
    return serialised


@app.get("/data/{record_id}", response_model=RecordOut)
async def get_record(record_id: int, session: AsyncSession = Depends(get_session)):
    cache_key = cache.key("record", str(record_id))
    cached = await cache.get_json(cache_key)
    if cached is not None:
        CACHE_HITS.inc()
        return cached

    CACHE_MISSES.inc()
    record = await crud.get_record(session, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    serialised = RecordOut.model_validate(record).model_dump()
    await cache.set_json(cache_key, serialised)
    return serialised
