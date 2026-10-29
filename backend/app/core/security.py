import base64
import hashlib
import hmac
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from pydantic import BaseModel, ConfigDict

from app.core.config import settings
from app.core.exceptions import AuthError

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 64
_SALT_BYTES = 16


class TokenPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sub: str
    username: str
    type: Literal["access", "refresh"]
    jti: str
    ver: int
    iat: int
    exp: int


def hash_password(password: str) -> str:
    salt = os.urandom(_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_SCRYPT_DKLEN,
    )
    return "scrypt${}${}${}${}${}".format(
        _SCRYPT_N,
        _SCRYPT_R,
        _SCRYPT_P,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(digest).decode("ascii"),
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, n_raw, r_raw, p_raw, salt_b64, digest_b64 = hashed_password.split("$")
        if algorithm != "scrypt":
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        actual = hashlib.scrypt(
            plain_password.encode("utf-8"),
            salt=salt,
            n=int(n_raw),
            r=int(r_raw),
            p=int(p_raw),
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def validate_password_strength(password: str) -> None:
    if len(password) < 8:
        raise ValueError("密码长度不能少于 8 位")
    if len(password) > 64:
        raise ValueError("密码长度不能超过 64 位")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValueError("密码必须同时包含字母和数字")
    if password.lower() in {"12345678", "password", "itam@123", "admin123"}:
        raise ValueError("密码过于简单，请更换更安全的密码")


def create_token(
    *,
    user_id: int,
    username: str,
    token_version: int,
    token_type: Literal["access", "refresh"],
    expires_delta: timedelta,
) -> tuple[str, TokenPayload]:
    now = datetime.now(timezone.utc)
    payload = TokenPayload(
        sub=str(user_id),
        username=username,
        type=token_type,
        jti=uuid.uuid4().hex,
        ver=token_version,
        iat=int(now.timestamp()),
        exp=int((now + expires_delta).timestamp()),
    )
    encoded = jwt.encode(
        payload.model_dump(),
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded, payload


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> TokenPayload:
    try:
        raw = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "jti", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("登录已过期，请重新登录", code=40101) from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("无效的登录凭证，请重新登录") from exc

    payload = TokenPayload.model_validate(raw)
    if payload.type != expected_type:
        raise AuthError("登录凭证类型错误")
    return payload
