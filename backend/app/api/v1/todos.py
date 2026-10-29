from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_context
from app.core.database import get_db
from app.core.response import ok
from app.services.permission_service import AuthContext
from app.services.todo_service import TodoService

router = APIRouter(prefix="/todos", tags=["待办中心"])


@router.get("/summary", summary="我的待办汇总")
async def todo_summary(
    limit: int = Query(5, ge=1, le=10, description="每种待办类型返回的条目数"),
    context: AuthContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db),
):
    result = await TodoService(session).summary(context, per_type=limit)
    return ok(result.model_dump(mode="json"))


@router.get("", summary="我的待办列表")
async def todo_list(
    category: str | None = Query(None, max_length=20),
    todo_type: str | None = Query(None, max_length=40),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    context: AuthContext = Depends(get_current_context),
    session: AsyncSession = Depends(get_db),
):
    result = await TodoService(session).list_items(
        context,
        category=category,
        todo_type=todo_type,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return ok(result.model_dump(mode="json"))
