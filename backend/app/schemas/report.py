from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class ReportStatusSlice(BaseModel):
    status: str
    label: str
    count: int
    value: float


class ReportDeptSlice(BaseModel):
    dept_id: int | None = None
    name: str
    count: int
    value: float


class ReportCategorySlice(BaseModel):
    category_id: int
    name: str
    count: int
    value: float


class ReportTrendPoint(BaseModel):
    month: str
    count: int
    value: float


class ReportMetrics(BaseModel):
    total_count: int
    total_value: float
    avg_value: float
    in_use_count: int
    in_stock_count: int
    idle_count: int
    idle_value: float
    repairing_count: int
    pending_scrap_count: int
    scrapped_count: int
    warranty_expiring_30d: int
    warranty_expired: int
    compliance_asset_count: int


class AssetReportOverviewOut(BaseModel):
    metrics: ReportMetrics
    status_distribution: list[ReportStatusSlice] = Field(default_factory=list)
    dept_distribution: list[ReportDeptSlice] = Field(default_factory=list)
    category_distribution: list[ReportCategorySlice] = Field(default_factory=list)
    purchase_trend: list[ReportTrendPoint] = Field(default_factory=list)
    data_scope_label: str
    generated_at: datetime


class ReportAssetRow(BaseModel):
    id: int
    asset_no: str
    name: str
    category_name: str | None = None
    model_name: str | None = None
    serial_no: str | None = None
    dept_name: str | None = None
    custodian_name: str | None = None
    status: str
    status_label: str
    purchase_date: date | None = None
    purchase_price: float | None = None
    warranty_end: date | None = None
    location: str | None = None
    supplier: str | None = None


class IdleAssetRow(ReportAssetRow):
    idle_since: datetime
    idle_days: int


class ReportAssetPage(BaseModel):
    items: list[ReportAssetRow]
    total: int
    page: int
    page_size: int


class IdleAssetPage(BaseModel):
    items: list[IdleAssetRow]
    total: int
    page: int
    page_size: int


class ComplianceIssueBrief(BaseModel):
    issue_type: str
    label: str
    severity: str


class ComplianceAssetRow(ReportAssetRow):
    issues: list[ComplianceIssueBrief] = Field(default_factory=list)


class ComplianceAssetPage(BaseModel):
    items: list[ComplianceAssetRow]
    total: int
    page: int
    page_size: int


class ComplianceIssueSummary(BaseModel):
    issue_type: str
    label: str
    severity: str
    count: int
    suggestion: str


class ComplianceSummaryOut(BaseModel):
    items: list[ComplianceIssueSummary]
    asset_count: int
    generated_at: datetime


class ReportDeptOption(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    level: int
    path: str


class ReportCategoryOption(BaseModel):
    id: int
    parent_id: int | None = None
    name: str
    level: int
    path: str
    category_type: str
    status: int


class ReportOptionsOut(BaseModel):
    departments: list[ReportDeptOption]
    categories: list[ReportCategoryOption]
