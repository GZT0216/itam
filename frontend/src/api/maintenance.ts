import { request } from '@/api/request'
import type {
  Maintenance,
  MaintenanceAssetPage,
  MaintenanceCreatePayload,
  MaintenancePage,
  MaintenancePriority,
  MaintenanceRecordPayload,
  MaintenanceStatus,
  RepairerOption,
} from '@/types/maintenance'

interface MaintenanceListQuery {
  page: number
  page_size: number
  keyword?: string
  status?: MaintenanceStatus
  priority?: MaintenancePriority
}

interface AssetOptionQuery {
  page: number
  page_size: number
  keyword?: string
}

export const maintenanceApi = {
  optionsAssets(params: AssetOptionQuery): Promise<MaintenanceAssetPage> {
    return request<MaintenanceAssetPage>({
      url: '/maintenances/options/assets',
      params,
    })
  },

  optionsRepairers(keyword?: string): Promise<RepairerOption[]> {
    return request<RepairerOption[]>({
      url: '/maintenances/options/repairers',
      params: keyword ? { keyword } : undefined,
    })
  },

  list(params: MaintenanceListQuery): Promise<MaintenancePage> {
    return request<MaintenancePage>({ url: '/maintenances', params })
  },

  create(payload: MaintenanceCreatePayload): Promise<Maintenance> {
    return request<Maintenance>({
      url: '/maintenances',
      method: 'post',
      data: payload,
    })
  },

  get(id: number): Promise<Maintenance> {
    return request<Maintenance>({ url: `/maintenances/${id}` })
  },

  approve(
    id: number,
    payload: {
      version: number
      repairer_id: number
      expected_date?: string | null
      comment?: string | null
    },
  ): Promise<Maintenance> {
    return request<Maintenance>({
      url: `/maintenances/${id}/approve`,
      method: 'post',
      data: payload,
    })
  },

  reject(id: number, comment?: string | null): Promise<Maintenance> {
    return request<Maintenance>({
      url: `/maintenances/${id}/reject`,
      method: 'post',
      data: { comment: comment || null },
    })
  },

  start(id: number): Promise<Maintenance> {
    return request<Maintenance>({
      url: `/maintenances/${id}/start`,
      method: 'post',
    })
  },

  addRecord(id: number, payload: MaintenanceRecordPayload): Promise<Maintenance> {
    return request<Maintenance>({
      url: `/maintenances/${id}/records`,
      method: 'post',
      data: payload,
    })
  },

  complete(
    id: number,
    payload: { repair_result: string; comment?: string | null },
  ): Promise<Maintenance> {
    return request<Maintenance>({
      url: `/maintenances/${id}/complete`,
      method: 'post',
      data: payload,
    })
  },

  accept(
    id: number,
    payload: { version: number; comment?: string | null },
  ): Promise<Maintenance> {
    return request<Maintenance>({
      url: `/maintenances/${id}/accept`,
      method: 'post',
      data: payload,
    })
  },

  cancel(id: number, reason?: string | null): Promise<Maintenance> {
    return request<Maintenance>({
      url: `/maintenances/${id}/cancel`,
      method: 'post',
      data: { reason: reason || null },
    })
  },
}
