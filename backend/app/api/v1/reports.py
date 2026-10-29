from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_perm
from app.core.database import get_db
from app.core.response import ok
from app.services.permission_service import AuthContext
from app.services.report_service import ReportFilters, ReportService

router = APIRouter(tags=["报表分析"])


def get_report_filters(
    keyword: str | None = Query(None, max_length=100),
    status: str | None = Query(None, max_length=20),
    category_id: int | None = Query(None, ge=1),
    include_child: bool = Query(True),
    dept_id: int | None = Query(None, ge=1),
    purchase_from: date | None = Query(None),
    purchase_to: date | None = Query(None),
) -> ReportFilters:
    return ReportFilters(
        keyword=keyword,
        status=status,
        category_id=category_id,
        include_child=include_child,
        dept_id=dept_id,
        purchase_from=purchase_from,
        purchase_to=purchase_to,
    )


@router.get("/reports/assets/options", summary="报表筛选项")
async def report_options(
    context: AuthContext = Depends(require_perm("asset:report:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReportService(session).options(context)
    return ok(result.model_dump(mode="json"))


@router.get("/reports/assets/overview", summary="资产分析概览")
async def report_overview(
    filters: ReportFilters = Depends(get_report_filters),
    context: AuthContext = Depends(require_perm("asset:report:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReportService(session).overview(context, filters)
    return ok(result.model_dump(mode="json"))


@router.get("/reports/assets", summary="资产清单报表")
async def report_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    filters: ReportFilters = Depends(get_report_filters),
    context: AuthContext = Depends(require_perm("asset:report:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReportService(session).assets_page(
        context, filters, page=page, page_size=page_size
    )
    return ok(result.model_dump(mode="json"))


@router.get("/reports/assets/idle", summary="闲置资产报表")
async def report_idle_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    filters: ReportFilters = Depends(get_report_filters),
    context: AuthContext = Depends(require_perm("asset:report:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReportService(session).idle_page(
        context, filters, page=page, page_size=page_size
    )
    return ok(result.model_dump(mode="json"))


@router.get("/reports/assets/compliance/summary", summary="合规检查汇总")
async def report_compliance_summary(
    filters: ReportFilters = Depends(get_report_filters),
    context: AuthContext = Depends(require_perm("asset:report:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReportService(session).compliance_summary(context, filters)
    return ok(result.model_dump(mode="json"))


@router.get("/reports/assets/compliance", summary="合规检查明细")
async def report_compliance_assets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    issue_type: str | None = Query(None, max_length=40),
    filters: ReportFilters = Depends(get_report_filters),
    context: AuthContext = Depends(require_perm("asset:report:view")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReportService(session).compliance_page(
        context,
        filters,
        issue_type=issue_type,
        page=page,
        page_size=page_size,
    )
    return ok(result.model_dump(mode="json"))


@router.get("/reports/assets/export", summary="导出资产报表")
async def export_report(
    report_type: Literal["OVERVIEW", "ASSETS", "IDLE", "COMPLIANCE"] = Query(
        "OVERVIEW", alias="report"
    ),
    export_format: Literal["XLSX", "PDF"] = Query("XLSX", alias="format"),
    issue_type: str | None = Query(None, max_length=40),
    filters: ReportFilters = Depends(get_report_filters),
    context: AuthContext = Depends(require_perm("asset:report:export")),
    session: AsyncSession = Depends(get_db),
):
    result = await ReportService(session).export(
        context,
        filters,
        report_type=report_type,
        export_format=export_format,
        issue_type=issue_type,
    )
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"',
            "Content-Length": str(len(result.content)),
            "X-Export-Rows": str(result.row_count),
        },
    )
