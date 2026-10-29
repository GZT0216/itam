from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_any_perm, require_perm
from app.core.database import get_db
from app.core.response import ok
from app.schemas.asset_ops import (
    InventoryAdjustmentCreate,
    InventoryAdjustmentReview,
    InventoryCancelPayload,
    InventoryCreate,
    InventoryItemUpdate,
    InventoryScanPayload,
    InventorySurplusCreate,
    OpsComment,
    OpsConfirmPayload,
    ScrapApprovePayload,
    ScrapCreate,
    TransferCreate,
)
from app.services.asset_ops_service import AssetOpsService
from app.services.inventory_service import InventoryService
from app.services.permission_service import AuthContext

router = APIRouter(tags=["资产运营"])


@router.get("/asset-ops/departments", summary="业务单据可选部门")
async def option_departments(
    context: AuthContext = Depends(
        require_any_perm(
            "asset:transfer:create", "asset:scrap:create", "asset:inventory:create"
        )
    ),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).option_departments(context)
    return ok(result)


@router.get("/asset-ops/users", summary="业务单据可选责任人")
async def option_users(
    keyword: str | None = Query(None, max_length=100),
    context: AuthContext = Depends(
        require_any_perm(
            "asset:transfer:create", "asset:scrap:create", "asset:inventory:create"
        )
    ),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).option_users(context, keyword)
    return ok(result)


@router.get("/asset-ops/categories", summary="业务单据可选分类")
async def option_categories(
    context: AuthContext = Depends(
        require_any_perm("asset:scrap:create", "asset:inventory:create")
    ),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).option_categories(context)
    return ok(result)


@router.get("/asset-ops/available-assets", summary="可调拨/报废资产")
async def operable_assets(
    purpose: str = Query("transfer", pattern="^(transfer|scrap)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, max_length=100),
    context: AuthContext = Depends(
        require_any_perm("asset:transfer:create", "asset:scrap:create")
    ),
    session: AsyncSession = Depends(get_db),
):
    items, total = await AssetOpsService(session).list_operable_assets(
        context,
        keyword=keyword,
        purpose=purpose,
        page=page,
        page_size=page_size,
    )
    return ok(
        {
            "items": [item.model_dump(mode="json") for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/asset-transfers", summary="调拨单列表")
async def list_transfers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, max_length=100),
    status: str | None = Query(None, max_length=24),
    context: AuthContext = Depends(require_perm("asset:transfer:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).list_transfers(
        context, keyword=keyword, status=status, page=page, page_size=page_size
    )
    return ok(result.model_dump(mode="json"))


@router.post("/asset-transfers", summary="发起资产调拨")
async def create_transfer(
    payload: TransferCreate,
    context: AuthContext = Depends(require_perm("asset:transfer:create")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).create_transfer(payload, context)
    return ok(result.model_dump(mode="json"), message="调拨申请已提交")


@router.get("/asset-transfers/{transfer_id}", summary="调拨单详情")
async def transfer_detail(
    transfer_id: int,
    context: AuthContext = Depends(require_perm("asset:transfer:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).get_transfer(transfer_id, context)
    return ok(result.model_dump(mode="json"))


@router.post("/asset-transfers/{transfer_id}/approve", summary="审批调拨")
async def approve_transfer(
    transfer_id: int,
    payload: OpsComment,
    context: AuthContext = Depends(require_perm("asset:transfer:approve")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).approve_transfer(
        transfer_id, payload.comment, context
    )
    return ok(result.model_dump(mode="json"), message="审批通过，等待确认调拨")


@router.post("/asset-transfers/{transfer_id}/reject", summary="驳回调拨")
async def reject_transfer(
    transfer_id: int,
    payload: OpsComment,
    context: AuthContext = Depends(require_perm("asset:transfer:approve")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).reject_transfer(
        transfer_id, payload.comment, context
    )
    return ok(result.model_dump(mode="json"), message="调拨单已驳回")


@router.post("/asset-transfers/{transfer_id}/cancel", summary="撤销调拨")
async def cancel_transfer(
    transfer_id: int,
    context: AuthContext = Depends(
        require_any_perm(
            "asset:transfer:cancel", "asset:transfer:approve", "asset:transfer:create"
        )
    ),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).cancel_transfer(transfer_id, context)
    return ok(result.model_dump(mode="json"), message="调拨单已撤销")


@router.post("/asset-transfers/{transfer_id}/confirm", summary="确认调拨")
async def confirm_transfer(
    transfer_id: int,
    payload: OpsConfirmPayload,
    context: AuthContext = Depends(require_perm("asset:transfer:confirm")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).confirm_transfer(
        transfer_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="调拨完成，资产信息已同步")


@router.get("/asset-scraps", summary="报废单列表")
async def list_scraps(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, max_length=100),
    status: str | None = Query(None, max_length=24),
    context: AuthContext = Depends(require_perm("asset:scrap:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).list_scraps(
        context, keyword=keyword, status=status, page=page, page_size=page_size
    )
    return ok(result.model_dump(mode="json"))


@router.post("/asset-scraps", summary="发起资产报废")
async def create_scrap(
    payload: ScrapCreate,
    context: AuthContext = Depends(require_perm("asset:scrap:create")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).create_scrap(payload, context)
    return ok(result.model_dump(mode="json"), message="报废申请已提交")


@router.get("/asset-scraps/{scrap_id}", summary="报废单详情")
async def scrap_detail(
    scrap_id: int,
    context: AuthContext = Depends(require_perm("asset:scrap:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).get_scrap(scrap_id, context)
    return ok(result.model_dump(mode="json"))


@router.post("/asset-scraps/{scrap_id}/approve", summary="审批报废")
async def approve_scrap(
    scrap_id: int,
    payload: ScrapApprovePayload,
    context: AuthContext = Depends(require_perm("asset:scrap:approve")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).approve_scrap(scrap_id, payload, context)
    return ok(result.model_dump(mode="json"), message="审批通过，资产转入待报废")


@router.post("/asset-scraps/{scrap_id}/reject", summary="驳回报废")
async def reject_scrap(
    scrap_id: int,
    payload: OpsComment,
    context: AuthContext = Depends(require_perm("asset:scrap:approve")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).reject_scrap(
        scrap_id, payload.comment, context
    )
    return ok(result.model_dump(mode="json"), message="报废单已驳回")


@router.post("/asset-scraps/{scrap_id}/cancel", summary="撤销报废")
async def cancel_scrap(
    scrap_id: int,
    context: AuthContext = Depends(
        require_any_perm(
            "asset:scrap:cancel", "asset:scrap:approve", "asset:scrap:create"
        )
    ),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).cancel_scrap(scrap_id, context)
    return ok(result.model_dump(mode="json"), message="报废单已撤销")


@router.post("/asset-scraps/{scrap_id}/confirm", summary="确认报废")
async def confirm_scrap(
    scrap_id: int,
    payload: OpsConfirmPayload,
    context: AuthContext = Depends(require_perm("asset:scrap:confirm")),
    session: AsyncSession = Depends(get_db),
):
    result = await AssetOpsService(session).confirm_scrap(scrap_id, payload, context)
    return ok(result.model_dump(mode="json"), message="报废完成，资产已标记为已报废")


@router.get("/inventory-tasks", summary="盘点任务列表")
async def list_inventory_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, max_length=100),
    status: str | None = Query(None, max_length=24),
    context: AuthContext = Depends(require_perm("asset:inventory:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).list_tasks(
        context, keyword=keyword, status=status, page=page, page_size=page_size
    )
    return ok(result.model_dump(mode="json"))


@router.post("/inventory-tasks", summary="创建盘点任务")
async def create_inventory_task(
    payload: InventoryCreate,
    context: AuthContext = Depends(require_perm("asset:inventory:create")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).create_task(payload, context)
    return ok(result.model_dump(mode="json"), message="盘点任务已创建")


@router.get("/inventory-tasks/{task_id}", summary="盘点任务详情")
async def inventory_task_detail(
    task_id: int,
    context: AuthContext = Depends(require_perm("asset:inventory:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).get_task(task_id, context)
    return ok(result.model_dump(mode="json"))


@router.get("/inventory-tasks/{task_id}/items", summary="盘点明细")
async def inventory_items(
    task_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    keyword: str | None = Query(None, max_length=100),
    result: str | None = Query(None, max_length=20),
    context: AuthContext = Depends(require_perm("asset:inventory:view")),
    session: AsyncSession = Depends(get_db),
):
    data = await InventoryService(session).list_items(
        task_id,
        context,
        keyword=keyword,
        result=result,
        page=page,
        page_size=page_size,
    )
    return ok(data.model_dump(mode="json"))


@router.post(
    "/inventory-tasks/{task_id}/items/{item_id}", summary="更新盘点明细"
)
async def update_inventory_item(
    task_id: int,
    item_id: int,
    payload: InventoryItemUpdate,
    context: AuthContext = Depends(require_perm("asset:inventory:manage")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).update_item(
        task_id, item_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="盘点结果已保存")


@router.post("/inventory-tasks/{task_id}/scan", summary="扫码盘点")
async def scan_inventory_item(
    task_id: int,
    payload: InventoryScanPayload,
    context: AuthContext = Depends(require_perm("asset:inventory:manage")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).scan(task_id, payload, context)
    return ok(result.model_dump(mode="json"), message="扫码盘点成功")


@router.post("/inventory-tasks/{task_id}/complete", summary="完成盘点")
async def complete_inventory_task(
    task_id: int,
    context: AuthContext = Depends(require_perm("asset:inventory:manage")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).complete(task_id, context)
    return ok(result.model_dump(mode="json"), message="盘点任务已完成")


@router.post("/inventory-tasks/{task_id}/cancel", summary="取消盘点")
async def cancel_inventory_task(
    task_id: int,
    payload: InventoryCancelPayload,
    context: AuthContext = Depends(require_perm("asset:inventory:manage")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).cancel(task_id, payload, context)
    return ok(result.model_dump(mode="json"), message="盘点任务已取消")


@router.get("/inventory-tasks/{task_id}/surplus-items", summary="盘盈资产明细")
async def list_inventory_surplus(
    task_id: int,
    context: AuthContext = Depends(require_perm("asset:inventory:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).list_surplus(task_id, context)
    return ok([item.model_dump(mode="json") for item in result])


@router.post("/inventory-tasks/{task_id}/surplus-items", summary="登记盘盈资产")
async def create_inventory_surplus(
    task_id: int,
    payload: InventorySurplusCreate,
    context: AuthContext = Depends(require_perm("asset:inventory:manage")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).add_surplus(task_id, payload, context)
    return ok(result.model_dump(mode="json"), message="盘盈资产已登记")


@router.delete(
    "/inventory-tasks/{task_id}/surplus-items/{surplus_id}",
    summary="删除盘盈登记",
)
async def delete_inventory_surplus(
    task_id: int,
    surplus_id: int,
    context: AuthContext = Depends(require_perm("asset:inventory:manage")),
    session: AsyncSession = Depends(get_db),
):
    await InventoryService(session).delete_surplus(task_id, surplus_id, context)
    return ok(None, message="盘盈登记已删除")


@router.post(
    "/inventory-tasks/{task_id}/adjustment", summary="提交盘盈盘亏处理"
)
async def submit_inventory_adjustment(
    task_id: int,
    payload: InventoryAdjustmentCreate,
    context: AuthContext = Depends(require_perm("asset:inventory:manage")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).submit_adjustment(
        task_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="盘盈盘亏处理单已提交")


@router.get(
    "/inventory-tasks/{task_id}/adjustment", summary="盘点盈亏处理单"
)
async def get_inventory_adjustment(
    task_id: int,
    context: AuthContext = Depends(require_perm("asset:inventory:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).get_adjustment(task_id, context)
    return ok(result.model_dump(mode="json") if result else None)


@router.post(
    "/inventory-tasks/{task_id}/adjustment/approve",
    summary="审批通过盘盈盘亏处理",
)
async def approve_inventory_adjustment(
    task_id: int,
    payload: InventoryAdjustmentReview,
    context: AuthContext = Depends(require_perm("asset:inventory:approve")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).approve_adjustment(
        task_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="盈亏处理已通过并执行")


@router.post(
    "/inventory-tasks/{task_id}/adjustment/reject",
    summary="驳回盘盈盘亏处理",
)
async def reject_inventory_adjustment(
    task_id: int,
    payload: InventoryAdjustmentReview,
    context: AuthContext = Depends(require_perm("asset:inventory:approve")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).reject_adjustment(
        task_id, payload, context
    )
    return ok(result.model_dump(mode="json"), message="盈亏处理已驳回")


@router.get("/inventory-tasks/{task_id}/report", summary="盘点报告")
async def inventory_report(
    task_id: int,
    context: AuthContext = Depends(require_perm("asset:inventory:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).report(task_id, context)
    return ok(result.model_dump(mode="json"))


@router.get("/inventory-tasks/{task_id}/report/export", summary="导出盘点报告")
async def export_inventory_report(
    task_id: int,
    context: AuthContext = Depends(require_perm("asset:report:export")),
    session: AsyncSession = Depends(get_db),
):
    result = await InventoryService(session).export_report(task_id, context)
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": (
                "attachment; filename=\"inventory_report.xlsx\"; "
                f"filename*=UTF-8''{quote(result.filename)}"
            ),
            "Content-Length": str(len(result.content)),
            "X-Export-Rows": str(result.row_count),
        },
    )
