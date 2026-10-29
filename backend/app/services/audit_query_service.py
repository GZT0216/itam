from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.permissions import DataScope
from app.models import User
from app.repositories.audit_repo import AuditLogRepository
from app.schemas.audit import (
    AuditFilterOptions,
    AuditLogDetail,
    AuditLogPage,
)
from app.services.permission_service import AuthContext
from app.services.scope_service import scoped_dept_ids


class AuditQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.logs = AuditLogRepository(session)

    async def _allowed_user_ids(self, context: AuthContext) -> set[int] | None:
        if context.is_superuser or context.data_scope == DataScope.ALL:
            return None
        if context.data_scope == DataScope.SELF:
            return {context.user.id}
        dept_ids = await scoped_dept_ids(self.session, context)
        if not dept_ids:
            return set()
        stmt = select(User.id).where(User.dept_id.in_(dept_ids))
        return set((await self.session.execute(stmt)).scalars().all())

    async def list(
        self,
        context: AuthContext,
        *,
        keyword: str | None,
        module: str | None,
        action: str | None,
        status: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        page: int,
        page_size: int,
    ) -> AuditLogPage:
        user_ids = await self._allowed_user_ids(context)
        rows, total = await self.logs.list_paginated(
            user_ids=user_ids,
            keyword=keyword,
            module=module,
            action=action,
            status=status,
            start_time=start_time,
            end_time=end_time,
            page=page,
            page_size=page_size,
        )
        return AuditLogPage(items=rows, total=total, page=page, page_size=page_size)

    async def detail(self, log_id: int, context: AuthContext) -> AuditLogDetail:
        log = await self.logs.get(log_id)
        if log is None:
            raise NotFoundError("审计日志不存在")
        user_ids = await self._allowed_user_ids(context)
        if user_ids is not None and (log.user_id is None or log.user_id not in user_ids):
            raise NotFoundError("审计日志不存在")
        return AuditLogDetail.model_validate(log)

    async def options(self, context: AuthContext) -> AuditFilterOptions:
        user_ids = await self._allowed_user_ids(context)
        modules, actions = await self.logs.filter_options(user_ids=user_ids)
        return AuditFilterOptions(modules=modules, actions=actions)
