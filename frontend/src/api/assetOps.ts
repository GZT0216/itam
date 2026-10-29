import { request } from '@/api/request'
import type {
  CategoryOption,
  DeptOption,
  InventoryAdjustmentItem,
  InventoryCreatePayload,
  InventoryItem,
  InventoryItemPage,
  InventoryItemUpdatePayload,
  InventoryReport,
  InventorySurplusCreatePayload,
  InventorySurplusItem,
  InventoryTaskItem,
  InventoryTaskPage,
  OpsAssetPage,
  OpsConfirmPayload,
  ScrapCreatePayload,
  ScrapItem,
  ScrapPage,
  TransferCreatePayload,
  TransferItem,
  TransferPage,
  UserOption,
} from '@/types/assetOps'

interface OpsListQuery {
  page: number
  page_size: number
  keyword?: string
  status?: string
}

export const assetOpsApi = {
  operableAssets(params: {
    purpose: 'transfer' | 'scrap'
    page: number
    page_size: number
    keyword?: string
  }): Promise<OpsAssetPage> {
    return request<OpsAssetPage>({ url: '/asset-ops/available-assets', params })
  },

  departments(): Promise<DeptOption[]> {
    return request<DeptOption[]>({ url: '/asset-ops/departments' })
  },

  users(keyword?: string): Promise<UserOption[]> {
    return request<UserOption[]>({
      url: '/asset-ops/users',
      params: keyword ? { keyword } : undefined,
    })
  },

  categories(): Promise<CategoryOption[]> {
    return request<CategoryOption[]>({ url: '/asset-ops/categories' })
  },

  listTransfers(params: OpsListQuery): Promise<TransferPage> {
    return request<TransferPage>({ url: '/asset-transfers', params })
  },

  createTransfer(payload: TransferCreatePayload): Promise<TransferItem> {
    return request<TransferItem>({
      url: '/asset-transfers',
      method: 'post',
      data: payload,
    })
  },

  getTransfer(id: number): Promise<TransferItem> {
    return request<TransferItem>({ url: `/asset-transfers/${id}` })
  },

  approveTransfer(id: number, comment?: string | null): Promise<TransferItem> {
    return request<TransferItem>({
      url: `/asset-transfers/${id}/approve`,
      method: 'post',
      data: { comment },
    })
  },

  rejectTransfer(id: number, comment: string): Promise<TransferItem> {
    return request<TransferItem>({
      url: `/asset-transfers/${id}/reject`,
      method: 'post',
      data: { comment },
    })
  },

  cancelTransfer(id: number): Promise<TransferItem> {
    return request<TransferItem>({
      url: `/asset-transfers/${id}/cancel`,
      method: 'post',
    })
  },

  confirmTransfer(id: number, payload: OpsConfirmPayload): Promise<TransferItem> {
    return request<TransferItem>({
      url: `/asset-transfers/${id}/confirm`,
      method: 'post',
      data: payload,
    })
  },

  listScraps(params: OpsListQuery): Promise<ScrapPage> {
    return request<ScrapPage>({ url: '/asset-scraps', params })
  },

  createScrap(payload: ScrapCreatePayload): Promise<ScrapItem> {
    return request<ScrapItem>({
      url: '/asset-scraps',
      method: 'post',
      data: payload,
    })
  },

  getScrap(id: number): Promise<ScrapItem> {
    return request<ScrapItem>({ url: `/asset-scraps/${id}` })
  },

  approveScrap(id: number, payload: OpsConfirmPayload): Promise<ScrapItem> {
    return request<ScrapItem>({
      url: `/asset-scraps/${id}/approve`,
      method: 'post',
      data: payload,
    })
  },

  rejectScrap(id: number, comment: string): Promise<ScrapItem> {
    return request<ScrapItem>({
      url: `/asset-scraps/${id}/reject`,
      method: 'post',
      data: { comment },
    })
  },

  cancelScrap(id: number): Promise<ScrapItem> {
    return request<ScrapItem>({
      url: `/asset-scraps/${id}/cancel`,
      method: 'post',
    })
  },

  confirmScrap(id: number, payload: OpsConfirmPayload): Promise<ScrapItem> {
    return request<ScrapItem>({
      url: `/asset-scraps/${id}/confirm`,
      method: 'post',
      data: payload,
    })
  },

  listInventoryTasks(params: OpsListQuery): Promise<InventoryTaskPage> {
    return request<InventoryTaskPage>({ url: '/inventory-tasks', params })
  },

  createInventoryTask(payload: InventoryCreatePayload): Promise<InventoryTaskItem> {
    return request<InventoryTaskItem>({
      url: '/inventory-tasks',
      method: 'post',
      data: payload,
    })
  },

  getInventoryTask(id: number): Promise<InventoryTaskItem> {
    return request<InventoryTaskItem>({ url: `/inventory-tasks/${id}` })
  },

  listInventoryItems(
    id: number,
    params: {
      page: number
      page_size: number
      keyword?: string
      result?: string
    },
  ): Promise<InventoryItemPage> {
    return request<InventoryItemPage>({
      url: `/inventory-tasks/${id}/items`,
      params,
    })
  },

  updateInventoryItem(
    taskId: number,
    itemId: number,
    payload: InventoryItemUpdatePayload,
  ): Promise<InventoryItem> {
    return request<InventoryItem>({
      url: `/inventory-tasks/${taskId}/items/${itemId}`,
      method: 'post',
      data: payload,
    })
  },

  scanInventoryItem(
    taskId: number,
    payload: InventoryItemUpdatePayload & { code: string },
  ): Promise<InventoryItem> {
    return request<InventoryItem>({
      url: `/inventory-tasks/${taskId}/scan`,
      method: 'post',
      data: payload,
    })
  },

  completeInventoryTask(id: number): Promise<InventoryTaskItem> {
    return request<InventoryTaskItem>({
      url: `/inventory-tasks/${id}/complete`,
      method: 'post',
    })
  },

  cancelInventoryTask(id: number, reason?: string | null): Promise<InventoryTaskItem> {
    return request<InventoryTaskItem>({
      url: `/inventory-tasks/${id}/cancel`,
      method: 'post',
      data: { reason },
    })
  },

  listInventorySurplus(id: number): Promise<InventorySurplusItem[]> {
    return request<InventorySurplusItem[]>({
      url: `/inventory-tasks/${id}/surplus-items`,
    })
  },

  addInventorySurplus(
    id: number,
    payload: InventorySurplusCreatePayload,
  ): Promise<InventorySurplusItem> {
    return request<InventorySurplusItem>({
      url: `/inventory-tasks/${id}/surplus-items`,
      method: 'post',
      data: payload,
    })
  },

  deleteInventorySurplus(id: number, surplusId: number): Promise<void> {
    return request<void>({
      url: `/inventory-tasks/${id}/surplus-items/${surplusId}`,
      method: 'delete',
    })
  },

  submitInventoryAdjustment(
    id: number,
    reason?: string | null,
  ): Promise<InventoryAdjustmentItem> {
    return request<InventoryAdjustmentItem>({
      url: `/inventory-tasks/${id}/adjustment`,
      method: 'post',
      data: { reason },
    })
  },

  getInventoryAdjustment(id: number): Promise<InventoryAdjustmentItem | null> {
    return request<InventoryAdjustmentItem | null>({
      url: `/inventory-tasks/${id}/adjustment`,
    })
  },

  approveInventoryAdjustment(
    id: number,
    payload: { version: number; comment?: string | null },
  ): Promise<InventoryAdjustmentItem> {
    return request<InventoryAdjustmentItem>({
      url: `/inventory-tasks/${id}/adjustment/approve`,
      method: 'post',
      data: payload,
    })
  },

  rejectInventoryAdjustment(
    id: number,
    payload: { version: number; comment: string },
  ): Promise<InventoryAdjustmentItem> {
    return request<InventoryAdjustmentItem>({
      url: `/inventory-tasks/${id}/adjustment/reject`,
      method: 'post',
      data: payload,
    })
  },

  getInventoryReport(id: number): Promise<InventoryReport> {
    return request<InventoryReport>({ url: `/inventory-tasks/${id}/report` })
  },

  exportInventoryReport(id: number): Promise<Blob> {
    return request<Blob>({
      url: `/inventory-tasks/${id}/report/export`,
      responseType: 'blob',
      timeout: 120000,
    })
  },
}
