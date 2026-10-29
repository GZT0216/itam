import type { AssetStatus } from '@/types/asset'

export type ReportType = 'OVERVIEW' | 'ASSETS' | 'IDLE' | 'COMPLIANCE'
export type ReportFormat = 'XLSX' | 'PDF'
export type ComplianceSeverity = 'warning' | 'info'

export interface ReportFilters {
  keyword?: string
  status?: AssetStatus
  category_id?: number
  include_child?: boolean
  dept_id?: number
  purchase_from?: string
  purchase_to?: string
}

export interface ReportStatusSlice {
  status: string
  label: string
  count: number
  value: number
}

export interface ReportDeptSlice {
  dept_id: number | null
  name: string
  count: number
  value: number
}

export interface ReportCategorySlice {
  category_id: number
  name: string
  count: number
  value: number
}

export interface ReportTrendPoint {
  month: string
  count: number
  value: number
}

export interface ReportMetrics {
  total_count: number
  total_value: number
  avg_value: number
  in_use_count: number
  in_stock_count: number
  idle_count: number
  idle_value: number
  repairing_count: number
  pending_scrap_count: number
  scrapped_count: number
  warranty_expiring_30d: number
  warranty_expired: number
  compliance_asset_count: number
}

export interface AssetReportOverview {
  metrics: ReportMetrics
  status_distribution: ReportStatusSlice[]
  dept_distribution: ReportDeptSlice[]
  category_distribution: ReportCategorySlice[]
  purchase_trend: ReportTrendPoint[]
  data_scope_label: string
  generated_at: string
}

export interface ReportAssetRow {
  id: number
  asset_no: string
  name: string
  category_name: string | null
  model_name: string | null
  serial_no: string | null
  dept_name: string | null
  custodian_name: string | null
  status: string
  status_label: string
  purchase_date: string | null
  purchase_price: number | null
  warranty_end: string | null
  location: string | null
  supplier: string | null
}

export interface IdleAssetRow extends ReportAssetRow {
  idle_since: string
  idle_days: number
}

export interface ReportAssetPage {
  items: ReportAssetRow[]
  total: number
  page: number
  page_size: number
}

export interface IdleAssetPage {
  items: IdleAssetRow[]
  total: number
  page: number
  page_size: number
}

export interface ComplianceIssueBrief {
  issue_type: string
  label: string
  severity: ComplianceSeverity
}

export interface ComplianceAssetRow extends ReportAssetRow {
  issues: ComplianceIssueBrief[]
}

export interface ComplianceAssetPage {
  items: ComplianceAssetRow[]
  total: number
  page: number
  page_size: number
}

export interface ComplianceIssueSummary {
  issue_type: string
  label: string
  severity: ComplianceSeverity
  count: number
  suggestion: string
}

export interface ComplianceSummary {
  items: ComplianceIssueSummary[]
  asset_count: number
  generated_at: string
}

export interface ReportDeptOption {
  id: number
  parent_id: number | null
  name: string
  level: number
  path: string
}

export interface ReportCategoryOption {
  id: number
  parent_id: number | null
  name: string
  level: number
  path: string
  category_type: string
  status: number
}

export interface ReportOptions {
  departments: ReportDeptOption[]
  categories: ReportCategoryOption[]
}

export interface TreeOption {
  value: number
  label: string
  disabled?: boolean
  children?: TreeOption[]
}

export interface ReportExportQuery extends ReportFilters {
  report: ReportType
  format: ReportFormat
  issue_type?: string
}
