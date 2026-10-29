import { request } from '@/api/request'
import type {
  AssetReportOverview,
  ComplianceAssetPage,
  ComplianceSummary,
  IdleAssetPage,
  ReportAssetPage,
  ReportExportQuery,
  ReportFilters,
  ReportOptions,
} from '@/types/report'

export const reportApi = {
  options(): Promise<ReportOptions> {
    return request<ReportOptions>({ url: '/reports/assets/options' })
  },

  overview(params: ReportFilters): Promise<AssetReportOverview> {
    return request<AssetReportOverview>({ url: '/reports/assets/overview', params })
  },

  assets(params: ReportFilters & { page: number; page_size: number }): Promise<ReportAssetPage> {
    return request<ReportAssetPage>({ url: '/reports/assets', params })
  },

  idle(params: ReportFilters & { page: number; page_size: number }): Promise<IdleAssetPage> {
    return request<IdleAssetPage>({ url: '/reports/assets/idle', params })
  },

  complianceSummary(params: ReportFilters): Promise<ComplianceSummary> {
    return request<ComplianceSummary>({
      url: '/reports/assets/compliance/summary',
      params,
    })
  },

  compliance(
    params: ReportFilters & { page: number; page_size: number; issue_type?: string },
  ): Promise<ComplianceAssetPage> {
    return request<ComplianceAssetPage>({ url: '/reports/assets/compliance', params })
  },

  exportReport(params: ReportExportQuery): Promise<Blob> {
    return request<Blob>({
      url: '/reports/assets/export',
      params,
      responseType: 'blob',
      timeout: 120000,
    })
  },
}
