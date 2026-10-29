from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.database import get_db
from app.core.response import ok
from app.schemas.approval_flow import (
    ApprovalFlowCreate,
    ApprovalFlowStatusUpdate,
    ApprovalFlowUpdate,
)
from app.services.approval_flow_service import ApprovalFlowService
from app.services.permission_service import AuthContext

router = APIRouter(prefix="/approval-flows", tags=["审批流程"])


@router.get("", summary="审批流程列表")
async def list_flows(
    context: AuthContext = Depends(require_perm("asset:request:flow:view")),
    session: AsyncSession = Depends(get_db),
):
    items = await ApprovalFlowService(session).list_flows(context)
    return ok([item.model_dump(mode="json") for item in items])


@router.get("/options", summary="审批流程配置选项")
async def flow_options(
    keyword: str | None = Query(None, max_length=100),
    context: AuthContext = Depends(require_perm("asset:request:flow:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await ApprovalFlowService(session).options(context, keyword=keyword)
    return ok(result.model_dump(mode="json"))


@router.post("", summary="新增审批流程")
async def create_flow(
    payload: ApprovalFlowCreate,
    context: AuthContext = Depends(require_perm("asset:request:flow:manage")),
    session: AsyncSession = Depends(get_db),
):
    result = await ApprovalFlowService(session).create_flow(payload, context)
    return ok(result.model_dump(mode="json"), message="审批流程已创建")


@router.put("/{flow_id}", summary="编辑审批流程")
async def update_flow(
    flow_id: int,
    payload: ApprovalFlowUpdate,
    context: AuthContext = Depends(require_perm("asset:request:flow:manage")),
    session: AsyncSession = Depends(get_db),
):
    result = await ApprovalFlowService(session).update_flow(
        flow_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="审批流程已更新")


@router.put("/{flow_id}/status", summary="启用/停用审批流程")
async def update_flow_status(
    flow_id: int,
    payload: ApprovalFlowStatusUpdate,
    context: AuthContext = Depends(require_perm("asset:request:flow:manage")),
    session: AsyncSession = Depends(get_db),
):
    result = await ApprovalFlowService(session).update_status(
        flow_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="审批流程状态已更新")
