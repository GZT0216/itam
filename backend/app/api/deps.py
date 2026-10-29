from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthError, PasswordChangeRequired, PermissionDenied
from app.core.security import decode_token
from app.core.token_store import get_token_store
from app.repositories.user_repo import UserRepository
from app.services.permission_service import AuthContext, PermissionService

bearer_scheme = HTTPBearer(auto_error=False)


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


async def get_current_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError("未登录或登录已过期")

    payload = decode_token(credentials.credentials, "access")
    store = get_token_store()
    if await store.is_access_blacklisted(payload.jti):
        raise AuthError("登录状态已失效，请重新登录")

    user = await UserRepository(session).get_with_relations(int(payload.sub))
    if user is None or user.status != 1:
        raise AuthError("账号不存在或已被停用", code=40102)
    if payload.ver != user.token_version:
        raise AuthError("登录状态已失效，请重新登录")

    return await PermissionService(session).build_context(
        user,
        access_jti=payload.jti,
        access_exp=payload.exp,
    )


def require_perm(code: str) -> Callable[..., Coroutine[Any, Any, AuthContext]]:
    async def dependency(
        context: AuthContext = Depends(get_current_context),
    ) -> AuthContext:
        if context.user.must_change_password:
            raise PasswordChangeRequired()
        if not context.has_permission(code):
            raise PermissionDenied(f"缺少操作权限：{code}")
        return context

    return dependency


def require_any_perm(*codes: str) -> Callable[..., Coroutine[Any, Any, AuthContext]]:
    async def dependency(
        context: AuthContext = Depends(get_current_context),
    ) -> AuthContext:
        if context.user.must_change_password:
            raise PasswordChangeRequired()
        if not any(context.has_permission(code) for code in codes):
            raise PermissionDenied("缺少操作权限")
        return context

    return dependency
