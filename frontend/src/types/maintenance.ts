import type { TagType } from '@/types/assetFlow'

export type MaintenanceStatus =
  | 'PENDING_APPROVAL'
  | 'PENDING_REPAIR'
  | 'REPAIRING'
  | 'PENDING_ACCEPTANCE'
  | 'COMPLETED'
  | 'REJECTED'
  | 'CANCELLED'

export type MaintenancePriority = 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT'
export type MaintenanceRecordType = 'PROGRESS' | 'EXPENSE'

export interface MaintenanceAsset {
  id: number
  asset_no: string
  name: string
  category_name: string | null
  model_name: string | null
  serial_no: string | null
  location: string | null
  dept_id: number | null
  dept_name: string | null
  custodian_id: number | null
  custodian_name: string | null
  status: string
  status_label: string
  version: number
}

export interface MaintenanceAssetPage {
  items: MaintenanceAsset[]
  total: number
  page: number
  page_size: number
}

export interface MaintenanceRecord {
  id: number
  record_type: MaintenanceRecordType
  record_type_label: string
  content: string
  cost: number | null
  operator_name: string | null
  occurred_at: string
  created_at: string
}

export interface Maintenance {
  id: number
  maintenance_no: string
  status: MaintenanceStatus
  status_label: string
  status_tag_type: TagType
  priority: MaintenancePriority
  priority_label: string
  priority_tag_type: TagType

  asset_id: number
  asset_no: string
  asset_name: string
  asset_version: number
  asset_status: string
  asset_status_label: string
  from_status: string
  from_status_label: string
  from_dept_id: number | null
  from_dept_name: string | null
  from_custodian_id: number | null
  from_custodian_name: string | null
  from_location: string | null

  fault_description: string
  expected_date: string | null
  applicant_id: number
  applicant_name: string
  applicant_dept_id: number | null
  applicant_dept_name: string | null

  approver_name: string | null
  approved_at: string | null
  approval_comment: string | null
  repairer_id: number | null
  repairer_name: string | null
  assigned_at: string | null
  started_at: string | null
  finished_at: string | null
  repair_result: string | null
  total_cost: number

  accepted_by_name: string | null
  accepted_at: string | null
  acceptance_comment: string | null
  cancelled_at: string | null
  cancel_reason: string | null

  records: MaintenanceRecord[]
  can_approve: boolean
  can_reject: boolean
  can_start: boolean
  can_add_record: boolean
  can_complete: boolean
  can_accept: boolean
  can_cancel: boolean

  version: number
  created_at: string
  updated_at: string
}

export interface MaintenancePage {
  items: Maintenance[]
  total: number
  page: number
  page_size: number
}

export interface RepairerOption {
  id: number
  name: string
  username: string
  dept_id: number | null
  dept_name: string | null
}

export interface MaintenanceCreatePayload {
  asset_id: number
  fault_description: string
  priority: MaintenancePriority
  expected_date?: string | null
}

export interface MaintenanceRecordPayload {
  record_type: MaintenanceRecordType
  content: string
  cost?: number | null
  occurred_at?: string | null
}

export const MAINTENANCE_STATUS_LABELS: Record<MaintenanceStatus, string> = {
  PENDING_APPROVAL: '待审批',
  PENDING_REPAIR: '待维修',
  REPAIRING: '维修中',
  PENDING_ACCEPTANCE: '待验收',
  COMPLETED: '已完成',
  REJECTED: '已驳回',
  CANCELLED: '已取消',
}

export const MAINTENANCE_PRIORITY_LABELS: Record<MaintenancePriority, string> = {
  LOW: '低',
  NORMAL: '普通',
  HIGH: '高',
  URGENT: '紧急',
}

export const MAINTENANCE_RECORD_TYPE_LABELS: Record<MaintenanceRecordType, string> = {
  PROGRESS: '维修记录',
  EXPENSE: '费用记录',
}

const MAINTENANCE_STEPS = ['提交报修', '审批指派', '维修中', '待验收', '完成']
const MAINTENANCE_ACTIVE: Record<MaintenanceStatus, number> = {
  PENDING_APPROVAL: 1,
  PENDING_REPAIR: 2,
  REPAIRING: 3,
  PENDING_ACCEPTANCE: 4,
  COMPLETED: 5,
  REJECTED: 1,
  CANCELLED: 1,
}

export function maintenanceSteps(): string[] {
  return MAINTENANCE_STEPS
}

export function maintenanceActive(status: MaintenanceStatus): number {
  return MAINTENANCE_ACTIVE[status] ?? 0
}

export function isMaintenanceInterrupted(status: MaintenanceStatus): boolean {
  return status === 'REJECTED' || status === 'CANCELLED'
}
