import time

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import create_access_token
from .config import settings
from .crud import (
    create_user,
    delete_user,
    get_user,
    get_user_by_email,
    update_user,
)
from .database import get_session
from .logging_config import configure_logging
from .schemas import TokenRequest, TokenResponse, UserCreate, UserOut, UserUpdate
from .tracing import setup_tracing

configure_logging(settings.log_level)
logger = structlog.get_logger(__name__)

app = FastAPI(title="User Service", version="1.0.0")
setup_tracing(app, "user-service")

REQUEST_COUNT = Counter(
    "user_requests_total", "Total requests", ["method", "path", "status"]
)
REQUEST_LATENCY = Histogram(
    "user_request_duration_seconds", "Request latency in seconds", ["method", "path"]
)


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
async def health():
    return {"status": "healthy", "service": "user-service"}


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/users", response_model=UserOut, status_code=201)
async def create(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    try:
        user = await create_user(session, payload)
    except IntegrityError as exc:
        await session.rollback()
        logger.info("user.create_conflict", email=payload.email)
        raise HTTPException(
            status_code=409, detail="Email already registered"
        ) from exc
    logger.info("user.created", user_id=user.id)
    return user


@app.get("/users/{user_id}", response_model=UserOut)
async def read(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put("/users/{user_id}", response_model=UserOut)
async def update(
    user_id: int, payload: UserUpdate, session: AsyncSession = Depends(get_session)
):
    user = await update_user(session, user_id, payload)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.delete("/users/{user_id}", status_code=204)
async def delete(user_id: int, session: AsyncSession = Depends(get_session)):
    deleted = await delete_user(session, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")


@app.post("/auth/token", response_model=TokenResponse)
async def issue_token(
    payload: TokenRequest, session: AsyncSession = Depends(get_session)
):
    user = await get_user_by_email(session, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    token, expires_in = create_access_token(subject=str(user.id), email=user.email)
    logger.info("auth.token_issued", user_id=user.id)
    return TokenResponse(access_token=token, expires_in=expires_in)
