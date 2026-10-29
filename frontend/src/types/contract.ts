import type { TagType } from '@/types/assetFlow'

export type ContractType = 'PURCHASE' | 'MAINTENANCE' | 'LEASE'
export type ContractStatus = 'ACTIVE' | 'EXPIRING' | 'EXPIRED' | 'TERMINATED'

export interface ContractDeptOption {
  id: number
  parent_id: number | null
  name: string
  level: number
  path: string
}

export interface ContractOwnerOption {
  id: number
  name: string
  username: string
  dept_id: number | null
  dept_name: string | null
}

export interface ContractAsset {
  id: number
  asset_no: string
  name: string
  category_name: string | null
  model_name: string | null
  serial_no: string | null
  location: string | null
  dept_name: string | null
  custodian_name: string | null
  status: string
  status_label: string
  linked_at: string
  linked_by_name: string | null
}

export interface ContractAssetOption {
  id: number
  asset_no: string
  name: string
  category_name: string | null
  model_name: string | null
  serial_no: string | null
  location: string | null
  dept_name: string | null
  custodian_name: string | null
  status: string
  status_label: string
  linked: boolean
}

export interface ContractAssetOptionPage {
  items: ContractAssetOption[]
  total: number
  page: number
  page_size: number
}

export interface Contract {
  id: number
  contract_no: string
  name: string
  contract_type: ContractType
  contract_type_label: string
  contract_type_tag_type: TagType
  status: ContractStatus
  status_label: string
  status_tag_type: TagType
  supplier: string | null
  amount: number | string
  sign_date: string | null
  start_date: string
  end_date: string
  days_to_expiry: number
  dept_id: number | null
  dept_name: string | null
  owner_id: number | null
  owner_name: string | null
  remark: string | null
  terminated_at: string | null
  terminate_reason: string | null
  created_by_name: string | null
  assets: ContractAsset[]
  asset_count: number
  can_edit: boolean
  can_terminate: boolean
  can_renew: boolean
  can_link_asset: boolean
  version: number
  created_at: string
  updated_at: string
}

export interface ContractPage {
  items: Contract[]
  total: number
  page: number
  page_size: number
}

export interface ContractSummary {
  active_count: number
  expiring_count: number
  expired_count: number
  terminated_count: number
  total_amount: number | string
  linked_asset_count: number
}

export interface ContractCreatePayload {
  name: string
  contract_type: ContractType
  supplier?: string | null
  amount: number | string
  sign_date?: string | null
  start_date: string
  end_date: string
  dept_id?: number | null
  owner_id?: number | null
  remark?: string | null
  asset_ids?: number[]
}

export interface ContractUpdatePayload
  extends Omit<ContractCreatePayload, 'asset_ids'> {
  version: number
}

export interface ContractListQuery {
  page: number
  page_size: number
  keyword?: string
  contract_type?: ContractType
  status?: ContractStatus
  dept_id?: number
}

export const CONTRACT_TYPE_OPTIONS: Array<{ value: ContractType; label: string }> = [
  { value: 'PURCHASE', label: '采购合同' },
  { value: 'MAINTENANCE', label: '维保合同' },
  { value: 'LEASE', label: '租赁合同' },
]

export const CONTRACT_STATUS_OPTIONS: Array<{ value: ContractStatus; label: string }> = [
  { value: 'ACTIVE', label: '生效中' },
  { value: 'EXPIRING', label: '即将到期' },
  { value: 'EXPIRED', label: '已到期' },
  { value: 'TERMINATED', label: '已终止' },
]
