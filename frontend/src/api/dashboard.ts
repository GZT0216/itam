import { request } from '@/api/request'
import type { DashboardSummary } from '@/types/dashboard'

export interface DashboardQuery {
  dept_id?: number
  months?: number
}

export const dashboardApi = {
  summary(params: DashboardQuery = {}): Promise<DashboardSummary> {
    return request<DashboardSummary>({ url: '/dashboard/summary', params })
  },
}
