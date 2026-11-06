from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from pwdlib import PasswordHash

from core.config import settings
from core.constants import TokenType
password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return password_hash.verify(
        plain_password,
        hashed_password
    )


def create_token(
    user_id: str,
    token_type: TokenType,
    token_version: int,
    expires_delta: timedelta
) -> str:

    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "type": token_type.value,
        "ver": token_version,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + expires_delta
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def create_access_token(
    user_id: str,
    token_version: int
) -> str:

    return create_token(
        user_id=user_id,
        token_type=TokenType.ACCESS,
        token_version=token_version,
        expires_delta=timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    )


def create_refresh_token(
    user_id: str,
    token_version: int
) -> str:

    return create_token(
        user_id=user_id,
        token_type=TokenType.REFRESH,
        token_version=token_version,
        expires_delta=timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    )


def create_password_reset_token(
    user_id: str
) -> str:

    return create_token(
        user_id=user_id,
        token_type=TokenType.PASSWORD_RESET,
        token_version=0,
        expires_delta=timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )
    )


def decode_token(token: str) -> dict:

    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )