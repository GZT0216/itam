from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.database import get_db
from app.core.response import ok
from app.services.audit_query_service import AuditQueryService
from app.services.permission_service import AuthContext

router = APIRouter(tags=["审计日志"])


@router.get("/audit-logs/options", summary="审计日志筛选项")
async def audit_options(
    context: AuthContext = Depends(require_perm("system:audit:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await AuditQueryService(session).options(context)
    return ok(result.model_dump(mode="json"))


@router.get("/audit-logs", summary="审计日志列表")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, max_length=100),
    module: str | None = Query(None, max_length=64),
    action: str | None = Query(None, max_length=64),
    status: str | None = Query(None, pattern="^(SUCCESS|FAILED)$"),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    context: AuthContext = Depends(require_perm("system:audit:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await AuditQueryService(session).list(
        context,
        keyword=keyword,
        module=module,
        action=action,
        status=status,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.get("/audit-logs/{log_id}", summary="审计日志详情")
async def audit_detail(
    log_id: int,
    context: AuthContext = Depends(require_perm("system:audit:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await AuditQueryService(session).detail(log_id, context)
    return ok(result.model_dump(mode="json"))
