import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.database import AsyncSessionLocal, get_db
from app.core.exceptions import BizError
from app.core.response import ok
from app.schemas.ldap import LdapConfigPayload, LdapConfigUpdate
from app.services.ldap_service import LdapSyncService
from app.services.permission_service import AuthContext

logger = logging.getLogger("itam.ldap")

router = APIRouter(prefix="/system/ldap", tags=["域控同步"])


async def _run_manual_sync(
    config_id: int,
    operator_id: int | None,
    operator_name: str | None,
) -> None:
    try:
        async with AsyncSessionLocal() as session:
            await LdapSyncService(session).run_sync(
                config_id=config_id,
                trigger_type="MANUAL",
                operator_id=operator_id,
                operator_name=operator_name,
            )
    except Exception:  # noqa: BLE001 - background task must not surface after response
        logger.exception("manual LDAP sync failed (config=%s)", config_id)


@router.get("/config", summary="获取域控同步配置")
async def get_config(
    context: AuthContext = Depends(require_perm("system:ldap:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await LdapSyncService(session).get_config_out()
    return ok(result.model_dump(mode="json"))


@router.put("/config", summary="保存域控同步配置")
async def save_config(
    payload: LdapConfigUpdate,
    context: AuthContext = Depends(require_perm("system:ldap:update")),
    session: AsyncSession = Depends(get_db),
):
    result = await LdapSyncService(session).save_config(payload, context)
    return ok(result.model_dump(mode="json"), message="域控配置已保存")


@router.post("/test", summary="测试域控连接")
async def test_config(
    payload: LdapConfigPayload,
    context: AuthContext = Depends(require_perm("system:ldap:update")),
    session: AsyncSession = Depends(get_db),
):
    result = await LdapSyncService(session).test_config(payload, context)
    return ok(
        result.model_dump(mode="json"),
        message="域控连接测试成功" if result.success else "域控连接测试失败",
    )


@router.get("/options", summary="默认角色与部门选项")
async def options(
    context: AuthContext = Depends(require_perm("system:ldap:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await LdapSyncService(session).options()
    return ok(result.model_dump(mode="json"))


@router.post("/sync", summary="手动触发域控同步")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    context: AuthContext = Depends(require_perm("system:ldap:sync")),
    session: AsyncSession = Depends(get_db),
):
    service = LdapSyncService(session)
    config = await service.get_config()
    if config is None:
        raise BizError("尚未配置域控同步")
    if not config.enabled:
        raise BizError("域控同步未启用，请先保存并启用配置")
    if config.last_sync_status == "RUNNING":
        raise BizError("已有同步任务正在执行，请稍后刷新同步日志")

    operator_name = context.user.real_name or context.user.username
    background_tasks.add_task(
        _run_manual_sync,
        config.id,
        context.user.id,
        operator_name,
    )
    return ok(
        {
            "accepted": True,
            "config_id": config.id,
            "trigger_type": "MANUAL",
        },
        message="同步任务已提交，完成后可在同步日志中查看结果",
    )


@router.get("/logs", summary="同步日志列表")
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, pattern="^(RUNNING|SUCCESS|PARTIAL|FAILED)$"),
    context: AuthContext = Depends(require_perm("system:ldap:view")),
    session: AsyncSession = Depends(get_db),
):
    items, total = await LdapSyncService(session).list_logs(
        page=page,
        page_size=page_size,
        status=status,
    )
    return ok(
        {
            "items": [item.model_dump(mode="json") for item in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/logs/{log_id}", summary="同步日志详情")
async def get_log(
    log_id: int,
    context: AuthContext = Depends(require_perm("system:ldap:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await LdapSyncService(session).get_log(log_id)
    return ok(result.model_dump(mode="json"))
