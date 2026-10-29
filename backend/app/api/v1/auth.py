from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_client_ip, get_current_context
from app.core.database import get_db
from app.core.response import ok
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
)
from app.services.auth_service import AuthService
from app.services.permission_service import AuthContext

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", summary="账号密码登录")
async def login(
    payload: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    result = await AuthService(session).login(payload, ip=get_client_ip(request))
    return ok(result.model_dump(mode="json"), message="登录成功")


@router.post("/refresh", summary="刷新访问令牌（刷新令牌一次性轮换）")
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_db),
):
    result = await AuthService(session).refresh(payload.refresh_token)
    return ok(result.model_dump(mode="json"))


@router.post("/logout", summary="退出登录")
async def logout(
    payload: LogoutRequest | None = None,
    context: AuthContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db),
):
    await AuthService(session).logout(
        context,
        payload.refresh_token if payload else None,
    )
    return ok(None, message="已退出登录")


@router.get("/me", summary="当前登录用户信息、菜单与权限")
async def me(context: AuthContext = Depends(get_current_context)):
    return ok(context.to_profile().model_dump(mode="json"))


@router.post("/change-password", summary="修改当前用户密码")
async def change_password(
    payload: ChangePasswordRequest,
    context: AuthContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db),
):
    result = await AuthService(session).change_password(context, payload)
    return ok(result.model_dump(mode="json"), message="密码修改成功，请使用新令牌")
