from datetime import timedelta

import pytest

from app.core.exceptions import AuthError
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_password_hash_and_verify():
    password = "S3cure-Pass"
    hashed = hash_password(password)
    assert hashed.startswith("scrypt$")
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong-password", hashed)
    assert not verify_password(password, "broken-hash")


def test_password_policy():
    with pytest.raises(ValueError):
        validate_password_strength("short1")
    with pytest.raises(ValueError):
        validate_password_strength("onlyletters")
    validate_password_strength("GoodPass123")


def test_token_round_trip_and_type_check():
    token, payload = create_token(
        user_id=1,
        username="admin",
        token_version=2,
        token_type="access",
        expires_delta=timedelta(minutes=5),
    )
    decoded = decode_token(token, "access")
    assert decoded.sub == "1"
    assert decoded.jti == payload.jti
    assert decoded.ver == 2

    with pytest.raises(AuthError):
        decode_token(token, "refresh")
