"""Password hashing and JWT issuing/verification.

We call ``bcrypt`` directly rather than through ``passlib``: passlib's last
release was 2020 and its bcrypt backend detection crashes against ``bcrypt>=5``.

Passwords are SHA-256 pre-hashed and base64-encoded before bcrypt sees them,
the way Django's ``BCryptSHA256PasswordHasher`` does. bcrypt silently ignores
input past 72 bytes, which would make every long password with a shared 72-byte
prefix interchangeable; pre-hashing collapses any length to a fixed 44 bytes so
the whole password always contributes.
"""

from __future__ import annotations

import base64
import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import bcrypt
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from app.core.config import settings

TokenType = Literal["access", "refresh"]


class TokenError(Exception):
    """Raised when a token is absent, malformed, expired or badly signed."""


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """The verified claims we care about, with JWT's cryptic names unpacked."""

    subject: str
    tenant_id: str | None
    role: str
    token_type: TokenType
    jti: str
    expires_at: datetime


# ---------------------------------------------------------------- passwords


def _prepare(password: str) -> bytes:
    return base64.b64encode(hashlib.sha256(password.encode("utf-8")).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("ascii")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(password), hashed.encode("ascii"))
    except (ValueError, TypeError):
        # Malformed or truncated hash in the database; never treat it as a match.
        return False


# ------------------------------------------------------------------- tokens


def _create_token(
    *,
    subject: str,
    tenant_id: str | None,
    role: str,
    token_type: TokenType,
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "sub": subject,
        "tid": tenant_id,
        "role": role,
        "type": token_type,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(
    *,
    subject: str,
    tenant_id: str | None,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    return _create_token(
        subject=subject,
        tenant_id=tenant_id,
        role=role,
        token_type="access",
        expires_delta=expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(
    *,
    subject: str,
    tenant_id: str | None,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    return _create_token(
        subject=subject,
        tenant_id=tenant_id,
        role=role,
        token_type="refresh",
        expires_delta=expires_delta
        or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> TokenPayload:
    try:
        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except JWTError as exc:
        raise TokenError("Token is invalid") from exc

    try:
        return TokenPayload(
            subject=claims["sub"],
            tenant_id=claims.get("tid"),
            role=claims["role"],
            token_type=claims["type"],
            jti=claims["jti"],
            expires_at=datetime.fromtimestamp(claims["exp"], tz=UTC),
        )
    except KeyError as exc:
        raise TokenError(f"Token is missing the {exc.args[0]!r} claim") from exc
