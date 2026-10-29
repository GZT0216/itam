import time
from typing import Protocol

from app.core.config import settings
from app.core.exceptions import ServiceUnavailable

_REFRESH_PREFIX = "itam:refresh:"
_BLACKLIST_PREFIX = "itam:access:blacklist:"


class TokenStore(Protocol):
    async def save_refresh(self, jti: str, user_id: int, ttl_seconds: int) -> None: ...

    async def consume_refresh(self, jti: str, user_id: int) -> bool: ...

    async def revoke_refresh(self, jti: str) -> None: ...

    async def blacklist_access(self, jti: str, ttl_seconds: int) -> None: ...

    async def is_access_blacklisted(self, jti: str) -> bool: ...

    async def close(self) -> None: ...


class MemoryTokenStore:
    """仅供本地测试使用；进程重启后会话失效。生产环境使用 RedisTokenStore。"""

    def __init__(self) -> None:
        self._refresh: dict[str, tuple[int, float]] = {}
        self._blacklist: dict[str, float] = {}

    def _purge(self) -> None:
        now = time.time()
        self._refresh = {k: v for k, v in self._refresh.items() if v[1] > now}
        self._blacklist = {k: v for k, v in self._blacklist.items() if v > now}

    async def save_refresh(self, jti: str, user_id: int, ttl_seconds: int) -> None:
        self._purge()
        self._refresh[jti] = (user_id, time.time() + ttl_seconds)

    async def consume_refresh(self, jti: str, user_id: int) -> bool:
        self._purge()
        record = self._refresh.pop(jti, None)
        return bool(record and record[0] == user_id)

    async def revoke_refresh(self, jti: str) -> None:
        self._refresh.pop(jti, None)

    async def blacklist_access(self, jti: str, ttl_seconds: int) -> None:
        self._blacklist[jti] = time.time() + max(ttl_seconds, 1)

    async def is_access_blacklisted(self, jti: str) -> bool:
        self._purge()
        return jti in self._blacklist

    async def close(self) -> None:
        self._refresh.clear()
        self._blacklist.clear()

    def clear(self) -> None:
        self._refresh.clear()
        self._blacklist.clear()


class RedisTokenStore:
    def __init__(self, url: str) -> None:
        from redis.asyncio import Redis

        self._client = Redis.from_url(url, decode_responses=True, socket_timeout=3)

    async def save_refresh(self, jti: str, user_id: int, ttl_seconds: int) -> None:
        try:
            await self._client.set(f"{_REFRESH_PREFIX}{jti}", str(user_id), ex=ttl_seconds)
        except Exception as exc:
            raise ServiceUnavailable("会话服务暂不可用，请稍后重试", code=50301) from exc

    async def consume_refresh(self, jti: str, user_id: int) -> bool:
        try:
            value = await self._client.getdel(f"{_REFRESH_PREFIX}{jti}")
        except Exception as exc:
            raise ServiceUnavailable("会话服务暂不可用，请稍后重试", code=50301) from exc
        return value == str(user_id)

    async def revoke_refresh(self, jti: str) -> None:
        try:
            await self._client.delete(f"{_REFRESH_PREFIX}{jti}")
        except Exception:
            pass

    async def blacklist_access(self, jti: str, ttl_seconds: int) -> None:
        try:
            await self._client.set(f"{_BLACKLIST_PREFIX}{jti}", "1", ex=max(ttl_seconds, 1))
        except Exception as exc:
            raise ServiceUnavailable("会话服务暂不可用，请稍后重试", code=50301) from exc

    async def is_access_blacklisted(self, jti: str) -> bool:
        try:
            return bool(await self._client.exists(f"{_BLACKLIST_PREFIX}{jti}"))
        except Exception as exc:
            raise ServiceUnavailable("会话服务暂不可用，请稍后重试", code=50301) from exc

    async def close(self) -> None:
        await self._client.aclose()


_store: TokenStore | None = None


def get_token_store() -> TokenStore:
    global _store
    if _store is None:
        if settings.TOKEN_STORE == "memory":
            _store = MemoryTokenStore()
        else:
            _store = RedisTokenStore(settings.REDIS_URL)
    return _store


async def close_token_store() -> None:
    global _store
    if _store is not None:
        await _store.close()
        _store = None


def reset_token_store() -> None:
    """测试辅助：丢弃当前 store，下一次获取时按配置重建。"""
    global _store
    _store = None
