from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.database import get_db
from app.core.response import ok
from app.services.permission_service import AuthContext
from app.services.reminder_service import ReminderService

router = APIRouter(prefix="/reminders", tags=["到期提醒"])


@router.get("/summary", summary="到期提醒汇总")
async def reminder_summary(
    context: AuthContext = Depends(require_perm("asset:reminder:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReminderService(session).summary(context)
    return ok(result.model_dump(mode="json"))


@router.get("", summary="到期提醒列表")
async def reminder_page(
    category: Literal["WARRANTY", "CONTRACT", "BORROW", "INVENTORY"] | None = Query(
        None
    ),
    level: Literal["danger", "warning", "info"] | None = Query(None),
    keyword: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    context: AuthContext = Depends(require_perm("asset:reminder:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReminderService(session).page(
        context,
        category=category,
        level=level,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.post("/scan", summary="执行到期提醒扫描")
async def reminder_scan(
    context: AuthContext = Depends(require_perm("asset:reminder:scan")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReminderService(session).scan(actor=context.user)
    return ok(result.model_dump(mode="json"))
