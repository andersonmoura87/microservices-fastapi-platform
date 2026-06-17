from datetime import UTC, datetime, timedelta

import jwt

from .config import settings


def create_access_token(subject: str, email: str) -> tuple[str, int]:
    expires_in = settings.jwt_expire_minutes * 60
    now = datetime.now(UTC)
    claims = {
        "sub": subject,
        "email": email,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    token = jwt.encode(claims, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in
