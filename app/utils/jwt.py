from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import jwt
from config import config


def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Creates a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=config.access_token_expire_minutes)

    to_encode.update({"exp": expire, "iat": now})
    encoded_jwt = jwt.encode(
        to_encode,
        config.jwt_secret_key,
        algorithm=config.jwt_algorithm,
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodes and validates a JWT token. Raises jwt.PyJWTError on failure."""
    payload = jwt.decode(
        token,
        config.jwt_secret_key,
        algorithms=[config.jwt_algorithm],
    )
    return payload
