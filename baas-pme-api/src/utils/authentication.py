"""Primitivas de senha, JWT e refresh token da identidade de usuário."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import secrets
from uuid import uuid4

import bcrypt
import jwt
from jwt import InvalidTokenError

from constants import JWT_ACCESS_TOKEN_MINUTES, JWT_SECRET
from errors import InvalidSchema


def hash_password(password: str) -> str:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise InvalidSchema("password must not exceed 72 UTF-8 bytes.")
    return bcrypt.hashpw(encoded, bcrypt.gensalt()).decode("utf-8")


def password_matches(password: str, password_hash: str) -> bool:
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        return False
    return bcrypt.checkpw(encoded, password_hash.encode("utf-8"))


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def refresh_token_hash(refresh_token: str) -> str:
    return sha256(refresh_token.encode("utf-8")).hexdigest()


def issue_access_token(user_key: str, session_key: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_key,
        "sid": session_key,
        "jti": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=JWT_ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=["HS256"],
            options={"require": ["sub", "sid", "jti", "exp"]},
        )
    except InvalidTokenError as error:
        raise ValueError("invalid access token") from error


def bearer_token(authorization: str | None) -> str | None:
    if authorization is None:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ValueError("invalid authorization header")
    return token
