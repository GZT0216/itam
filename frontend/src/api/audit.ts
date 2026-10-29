import { request } from '@/api/request'
import type {
  AuditFilterOptions,
  AuditLogDetail,
  AuditLogPage,
  AuditQuery,
} from '@/types/audit'

export const auditApi = {
  listLogs(params: AuditQuery): Promise<AuditLogPage> {
    return request<AuditLogPage>({ url: '/audit-logs', params })
  },

  getLog(id: number): Promise<AuditLogDetail> {
    return request<AuditLogDetail>({ url: `/audit-logs/${id}` })
  },

  options(): Promise<AuditFilterOptions> {
    return request<AuditFilterOptions>({ url: '/audit-logs/options' })
  },
}
