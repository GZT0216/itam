import { request } from '@/api/request'
import type {
  Contract,
  ContractAssetOptionPage,
  ContractCreatePayload,
  ContractDeptOption,
  ContractListQuery,
  ContractOwnerOption,
  ContractPage,
  ContractSummary,
  ContractUpdatePayload,
} from '@/types/contract'

export const contractApi = {
  departments(): Promise<ContractDeptOption[]> {
    return request<ContractDeptOption[]>({ url: '/contracts/options/departments' })
  },

  owners(keyword?: string): Promise<ContractOwnerOption[]> {
    return request<ContractOwnerOption[]>({
      url: '/contracts/options/owners',
      params: keyword ? { keyword } : undefined,
    })
  },

  assets(params: {
    page: number
    page_size: number
    keyword?: string
    contract_id?: number
  }): Promise<ContractAssetOptionPage> {
    return request<ContractAssetOptionPage>({
      url: '/contracts/options/assets',
      params,
    })
  },

  summary(): Promise<ContractSummary> {
    return request<ContractSummary>({ url: '/contracts/summary' })
  },

  list(params: ContractListQuery): Promise<ContractPage> {
    return request<ContractPage>({ url: '/contracts', params })
  },

  get(id: number): Promise<Contract> {
    return request<Contract>({ url: `/contracts/${id}` })
  },

  create(payload: ContractCreatePayload): Promise<Contract> {
    return request<Contract>({ url: '/contracts', method: 'post', data: payload })
  },

  update(id: number, payload: ContractUpdatePayload): Promise<Contract> {
    return request<Contract>({
      url: `/contracts/${id}`,
      method: 'put',
      data: payload,
    })
  },

  terminate(id: number, version: number, reason: string): Promise<Contract> {
    return request<Contract>({
      url: `/contracts/${id}/terminate`,
      method: 'post',
      data: { version, reason },
    })
  },

  renew(
    id: number,
    payload: { version: number; end_date: string; amount?: number | string; remark?: string },
  ): Promise<Contract> {
    return request<Contract>({
      url: `/contracts/${id}/renew`,
      method: 'post',
      data: payload,
    })
  },

  linkAssets(id: number, assetIds: number[]): Promise<Contract> {
    return request<Contract>({
      url: `/contracts/${id}/assets`,
      method: 'post',
      data: { asset_ids: assetIds },
    })
  },

  unlinkAsset(id: number, assetId: number): Promise<Contract> {
    return request<Contract>({
      url: `/contracts/${id}/assets/${assetId}`,
      method: 'delete',
    })
  },
}
