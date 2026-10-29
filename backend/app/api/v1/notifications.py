from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_context
from app.core.database import get_db
from app.core.response import ok
from app.services.notification_service import NotificationService
from app.services.permission_service import AuthContext

router = APIRouter(prefix="/notifications", tags=["通知中心"])


@router.get("/summary", summary="通知中心汇总")
async def notification_summary(
    context: AuthContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db),
):
    result = await NotificationService(session).summary(context)
    return ok(result.model_dump(mode="json"))
