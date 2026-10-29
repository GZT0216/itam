import { request } from '@/api/request'
import type {
  ApprovalFlowItem,
  ApprovalFlowOptions,
  ApprovalFlowPayload,
  ApprovalFlowUpdatePayload,
} from '@/types/approvalFlow'

export const approvalFlowApi = {
  list(): Promise<ApprovalFlowItem[]> {
    return request<ApprovalFlowItem[]>({ url: '/approval-flows' })
  },

  options(keyword?: string): Promise<ApprovalFlowOptions> {
    return request<ApprovalFlowOptions>({
      url: '/approval-flows/options',
      params: keyword ? { keyword } : undefined,
    })
  },

  create(payload: ApprovalFlowPayload): Promise<ApprovalFlowItem> {
    return request<ApprovalFlowItem>({
      url: '/approval-flows',
      method: 'post',
      data: payload,
    })
  },

  update(id: number, payload: ApprovalFlowUpdatePayload): Promise<ApprovalFlowItem> {
    return request<ApprovalFlowItem>({
      url: `/approval-flows/${id}`,
      method: 'put',
      data: payload,
    })
  },

  updateStatus(
    id: number,
    payload: { status: number; version: number },
  ): Promise<ApprovalFlowItem> {
    return request<ApprovalFlowItem>({
      url: `/approval-flows/${id}/status`,
      method: 'put',
      data: payload,
    })
  },
}
