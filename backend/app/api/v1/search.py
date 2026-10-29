from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_context
from app.core.database import get_db
from app.core.response import ok
from app.services.permission_service import AuthContext
from app.services.search_service import SearchService

router = APIRouter(tags=["全局搜索"])


@router.get("/search", summary="全局搜索（资产编号/序列号/人员/部门）")
async def global_search(
    keyword: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(5, ge=1, le=10),
    context: AuthContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db),
):
    result = await SearchService(session).search(context, keyword, limit=limit)
    return ok(result.model_dump(mode="json"))
