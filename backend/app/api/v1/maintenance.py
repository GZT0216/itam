from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_perm, require_perm
from app.core.database import get_db
from app.core.response import ok
from app.schemas.maintenance import (
    MaintenanceAcceptPayload,
    MaintenanceApprovePayload,
    MaintenanceCancelPayload,
    MaintenanceComment,
    MaintenanceCompletePayload,
    MaintenanceCreate,
    MaintenanceRecordCreate,
)
from app.services.maintenance_service import MaintenanceService
from app.services.permission_service import AuthContext

router = APIRouter(tags=["维修管理"])


@router.get("/maintenances/options/assets", summary="可报修资产")
async def option_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, max_length=100),
    context: AuthContext = Depends(
        require_any_perm(
            "asset:maintenance:view",
            "asset:maintenance:create",
            "asset:maintenance:repair",
        )
    ),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).option_assets(
        context, keyword=keyword, page=page, page_size=page_size
    )
    return ok(result.model_dump(mode="json"))


@router.get("/maintenances/options/repairers", summary="可选维修人员")
async def option_repairers(
    keyword: str | None = Query(None, max_length=100),
    context: AuthContext = Depends(
        require_any_perm("asset:maintenance:approve", "asset:maintenance:repair")
    ),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).option_repairers(keyword)
    return ok(result)


@router.get("/maintenances", summary="维修工单列表")
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, max_length=100),
    status: str | None = Query(None, max_length=24),
    priority: str | None = Query(None, max_length=16),
    context: AuthContext = Depends(require_perm("asset:maintenance:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).list_orders(
        context,
        keyword=keyword,
        status=status,
        priority=priority,
        page=page,
        page_size=page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.post("/maintenances", summary="提交报修申请")
async def create_order(
    payload: MaintenanceCreate,
    context: AuthContext = Depends(require_perm("asset:maintenance:create")),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).create_order(payload, context)
    return ok(result.model_dump(mode="json"), message="报修申请已提交")


@router.get("/maintenances/{order_id}", summary="维修工单详情")
async def order_detail(
    order_id: int,
    context: AuthContext = Depends(require_perm("asset:maintenance:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).get_order(order_id, context)
    return ok(result.model_dump(mode="json"))


@router.post("/maintenances/{order_id}/approve", summary="审批并指派维修")
async def approve_order(
    order_id: int,
    payload: MaintenanceApprovePayload,
    context: AuthContext = Depends(require_perm("asset:maintenance:approve")),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).approve_order(
        order_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="审批通过，资产已转入维修中")


@router.post("/maintenances/{order_id}/reject", summary="驳回维修申请")
async def reject_order(
    order_id: int,
    payload: MaintenanceComment,
    context: AuthContext = Depends(require_perm("asset:maintenance:approve")),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).reject_order(
        order_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="维修申请已驳回")


@router.post("/maintenances/{order_id}/start", summary="开始维修")
async def start_repair(
    order_id: int,
    context: AuthContext = Depends(require_perm("asset:maintenance:repair")),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).start_repair(order_id, context)
    return ok(result.model_dump(mode="json"), message="已开始维修")


@router.post("/maintenances/{order_id}/records", summary="登记维修/费用记录")
async def add_record(
    order_id: int,
    payload: MaintenanceRecordCreate,
    context: AuthContext = Depends(require_perm("asset:maintenance:repair")),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).add_record(order_id, payload, context)
    return ok(result.model_dump(mode="json"), message="维修记录已保存")


@router.post("/maintenances/{order_id}/complete", summary="完成维修")
async def complete_repair(
    order_id: int,
    payload: MaintenanceCompletePayload,
    context: AuthContext = Depends(require_perm("asset:maintenance:repair")),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).complete_repair(
        order_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="维修已完成，等待验收")


@router.post("/maintenances/{order_id}/accept", summary="验收维修")
async def accept_order(
    order_id: int,
    payload: MaintenanceAcceptPayload,
    context: AuthContext = Depends(require_perm("asset:maintenance:accept")),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).accept_order(order_id, payload, context)
    return ok(result.model_dump(mode="json"), message="验收完成，资产已恢复原状态")


@router.post("/maintenances/{order_id}/cancel", summary="取消维修")
async def cancel_order(
    order_id: int,
    payload: MaintenanceCancelPayload,
    context: AuthContext = Depends(
        require_any_perm(
            "asset:maintenance:cancel",
            "asset:maintenance:approve",
            "asset:maintenance:create",
        )
    ),
    session: AsyncSession = Depends(get_db),
):
    result = await MaintenanceService(session).cancel_order(order_id, payload, context)
    return ok(result.model_dump(mode="json"), message="维修工单已取消")
