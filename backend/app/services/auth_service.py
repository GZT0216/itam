import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthError, BizError
from app.core.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.token_store import TokenStore, get_token_store
from app.models import User
from app.models.base import now_cst
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LoginUserInfo,
    TokenBundle,
)
from app.services.audit_service import AuditService
from app.services.ldap_service import authenticate_ldap_user, get_active_ldap_config
from app.services.permission_service import AuthContext

_DUMMY_HASH = hash_password("dummy-password-for-timing-1")


class AuthService:
    def __init__(self, session: AsyncSession, store: TokenStore | None = None) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.audit = AuditService(session)
        self.store = store or get_token_store()

    async def login(self, payload: LoginRequest, *, ip: str | None = None) -> LoginResponse:
        user = await self.users.get_by_username(payload.username)

        if user is None:
            verify_password(payload.password, _DUMMY_HASH)
            await self.audit.record(
                action="auth.login",
                module="认证",
                summary="登录失败：用户名或密码错误",
                actor_name=payload.username,
                status="FAILED",
            )
            await self.session.commit()
            raise AuthError("用户名或密码错误")

        if user.status != 1:
            await self.audit.record(
                action="auth.login",
                module="认证",
                summary="登录失败：账号已停用",
                actor=user,
                status="FAILED",
            )
            await self.session.commit()
            raise AuthError("账号已被停用，请联系管理员", code=40102)

        login_note = ""
        if user.source == "ldap":
            config = await get_active_ldap_config(self.session)
            if config is None:
                await self._record_failed_login(user, "登录失败：域控同步未启用")
                raise AuthError("域控同步未启用，域账号暂时无法登录，请联系管理员", code=40103)
            authenticated, message, service_unavailable = await asyncio.to_thread(
                authenticate_ldap_user, config, user, payload.password
            )
            if not authenticated:
                if service_unavailable and verify_password(payload.password, user.password_hash):
                    login_note = "（域控不可用，使用本地应急密码）"
                else:
                    detail = message if service_unavailable else "用户名或密码错误"
                    await self._record_failed_login(user, f"登录失败：{detail}")
                    raise AuthError(
                        detail if service_unavailable else "用户名或密码错误",
                        code=40104 if service_unavailable else 40101,
                    )
            else:
                login_note = "（域控认证）"
        elif not verify_password(payload.password, user.password_hash):
            await self._record_failed_login(user, "登录失败：用户名或密码错误")
            raise AuthError("用户名或密码错误")

        user.last_login_at = now_cst()
        user.last_login_ip = ip
        await self.audit.record(
            action="auth.login",
            module="认证",
            summary=f"登录成功{login_note}",
            actor=user,
            resource_type="user",
            resource_id=user.id,
        )
        await self.session.commit()

        bundle = await self._issue_pair(user)
        return LoginResponse(
            **bundle.model_dump(),
            must_change_password=user.must_change_password,
            user=LoginUserInfo(
                id=user.id,
                username=user.username,
                real_name=user.real_name,
                dept_name=user.dept.name if user.dept else None,
                avatar=user.avatar,
            ),
        )

    async def _record_failed_login(self, user: User, summary: str) -> None:
        await self.audit.record(
            action="auth.login",
            module="认证",
            summary=summary,
            actor=user,
            status="FAILED",
        )
        await self.session.commit()

    async def refresh(self, refresh_token: str) -> TokenBundle:
        token_payload = decode_token(refresh_token, "refresh")
        user = await self.users.get_with_relations(int(token_payload.sub))
        if user is None or user.status != 1:
            raise AuthError("账号不存在或已被停用", code=40102)
        if token_payload.ver != user.token_version:
            raise AuthError("登录状态已失效，请重新登录")

        if not await self.store.consume_refresh(token_payload.jti, user.id):
            raise AuthError("刷新凭证已失效，请重新登录")

        return await self._issue_pair(user)

    async def logout(self, context: AuthContext, refresh_token: str | None) -> None:
        ttl = max(1, context.access_exp - int(datetime.now(timezone.utc).timestamp()))
        await self.store.blacklist_access(context.access_jti, ttl)

        if refresh_token:
            try:
                refresh_payload = decode_token(refresh_token, "refresh")
                await self.store.revoke_refresh(refresh_payload.jti)
            except AuthError:
                pass

        await self.audit.record(
            action="auth.logout",
            module="认证",
            summary="退出登录",
            actor=context.user,
            resource_type="user",
            resource_id=context.user.id,
        )
        await self.session.commit()

    async def change_password(
        self,
        context: AuthContext,
        payload: ChangePasswordRequest,
    ) -> TokenBundle:
        user: User = context.user
        if user.source == "ldap":
            raise BizError("域控账号的密码由 AD 域管理，无法在系统中修改")
        if not verify_password(payload.old_password, user.password_hash):
            await self.audit.record(
                action="auth.change_password",
                module="认证",
                summary="修改密码失败：当前密码不正确",
                actor=user,
                status="FAILED",
            )
            await self.session.commit()
            raise BizError("当前密码不正确", code=40010)

        user.password_hash = hash_password(payload.new_password)
        user.must_change_password = False
        user.token_version += 1
        await self.audit.record(
            action="auth.change_password",
            module="认证",
            summary="修改密码成功，历史令牌已全部失效",
            actor=user,
            resource_type="user",
            resource_id=user.id,
            after={"must_change_password": False, "token_version": user.token_version},
        )
        await self.session.commit()

        return await self._issue_pair(user)

    async def _issue_pair(self, user: User) -> TokenBundle:
        access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        access_token, _ = create_token(
            user_id=user.id,
            username=user.username,
            token_version=user.token_version,
            token_type="access",
            expires_delta=access_expires,
        )
        refresh_token, refresh_payload = create_token(
            user_id=user.id,
            username=user.username,
            token_version=user.token_version,
            token_type="refresh",
            expires_delta=refresh_expires,
        )
        await self.store.save_refresh(
            refresh_payload.jti,
            user.id,
            int(refresh_expires.total_seconds()),
        )
        return TokenBundle(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(access_expires.total_seconds()),
        )
