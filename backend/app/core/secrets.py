import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.core.exceptions import BizError


def _fernet() -> Fernet:
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:itam-secret".encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise BizError("加密配置无法解密，请在域控同步页面重新保存绑定密码") from exc
