from datetime import datetime

from sqlalchemy import func, or_, select

from app.models import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog

    @staticmethod
    def _filters(
        *,
        user_ids: set[int] | None,
        keyword: str | None,
        module: str | None,
        action: str | None,
        status: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
    ) -> list:
        conditions: list = []
        if user_ids is not None:
            conditions.append(AuditLog.user_id.in_(user_ids))
        if keyword:
            like = f"%{keyword}%"
            conditions.append(
                or_(
                    AuditLog.username.like(like),
                    AuditLog.summary.like(like),
                    AuditLog.action.like(like),
                    AuditLog.resource_id.like(like),
                )
            )
        if module:
            conditions.append(AuditLog.module == module)
        if action:
            conditions.append(AuditLog.action == action)
        if status:
            conditions.append(AuditLog.status == status)
        if start_time is not None:
            conditions.append(AuditLog.created_at >= start_time)
        if end_time is not None:
            conditions.append(AuditLog.created_at <= end_time)
        return conditions

    async def list_paginated(
        self,
        *,
        user_ids: set[int] | None,
        keyword: str | None,
        module: str | None,
        action: str | None,
        status: str | None,
        start_time: datetime | None,
        end_time: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[AuditLog], int]:
        conditions = self._filters(
            user_ids=user_ids,
            keyword=keyword,
            module=module,
            action=action,
            status=status,
            start_time=start_time,
            end_time=end_time,
        )
        count_stmt = select(func.count()).select_from(AuditLog).where(*conditions)
        total = int(await self.session.scalar(count_stmt) or 0)
        if total == 0:
            return [], 0
        stmt = (
            select(AuditLog)
            .where(*conditions)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return rows, total

    async def filter_options(
        self,
        *,
        user_ids: set[int] | None,
    ) -> tuple[list[str], list[str]]:
        conditions: list = []
        if user_ids is not None:
            conditions.append(AuditLog.user_id.in_(user_ids))
        modules = list(
            (
                await self.session.execute(
                    select(AuditLog.module)
                    .where(*conditions)
                    .distinct()
                    .order_by(AuditLog.module)
                )
            )
            .scalars()
            .all()
        )
        actions = list(
            (
                await self.session.execute(
                    select(AuditLog.action)
                    .where(*conditions)
                    .distinct()
                    .order_by(AuditLog.action)
                )
            )
            .scalars()
            .all()
        )
        return modules, actions
