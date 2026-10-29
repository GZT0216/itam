export type ApproverType = 'DEPT_MANAGER' | 'USER' | 'ROLE'
export type ApproveMode = 'OR' | 'ALL'
export type FallbackType = 'ASSET_ADMIN' | 'DEPT_ADMIN' | 'SUPER_ADMIN' | 'SKIP'

export interface ApprovalFlowNodeInput {
  name: string
  approver_type: ApproverType
  user_id: number | null
  role_code: string | null
  manager_level: number
  approve_mode: ApproveMode
  fallback_type: FallbackType
}

export interface ApprovalFlowNode {
  id: number
  step_no: number
  step_code: string
  name: string
  approver_type: ApproverType
  approver_type_label: string
  user_id: number | null
  user_name: string | null
  role_code: string | null
  role_name: string | null
  manager_level: number
  approve_mode: ApproveMode
  approve_mode_label: string
  fallback_type: FallbackType
  fallback_type_label: string
}

export interface ApprovalFlowItem {
  id: number
  name: string
  description: string | null
  is_default: boolean
  status: number
  status_label: string
  dept_ids: number[]
  dept_names: string[]
  nodes: ApprovalFlowNode[]
  version: number
  created_by_name: string | null
  updated_by_name: string | null
  created_at: string
  updated_at: string
}

export interface ApprovalFlowPayload {
  name: string
  description: string | null
  is_default: boolean
  status: number
  dept_ids: number[]
  nodes: ApprovalFlowNodeInput[]
}

export interface ApprovalFlowUpdatePayload extends ApprovalFlowPayload {
  version: number
}

export interface FlowDeptOption {
  id: number
  name: string
  path: string
  level: number
  manager_id: number | null
  manager_name: string | null
}

export interface FlowUserOption {
  id: number
  username: string
  real_name: string
  dept_id: number | null
  dept_name: string | null
  status: number
}

export interface FlowRoleOption {
  code: string
  name: string
  data_scope: string
}

export interface ApprovalFlowOptions {
  departments: FlowDeptOption[]
  users: FlowUserOption[]
  roles: FlowRoleOption[]
}

export const APPROVER_TYPE_OPTIONS: Array<{ value: ApproverType; label: string }> = [
  { value: 'DEPT_MANAGER', label: '部门负责人' },
  { value: 'USER', label: '指定用户' },
  { value: 'ROLE', label: '指定角色' },
]

export const APPROVE_MODE_OPTIONS: Array<{ value: ApproveMode; label: string }> = [
  { value: 'OR', label: '或签（一人通过即可）' },
  { value: 'ALL', label: '会签（全部通过）' },
]

export const FALLBACK_OPTIONS: Array<{ value: FallbackType; label: string }> = [
  { value: 'ASSET_ADMIN', label: '转资产管理员' },
  { value: 'DEPT_ADMIN', label: '转部门管理员' },
  { value: 'SUPER_ADMIN', label: '转超级管理员' },
  { value: 'SKIP', label: '自动跳过该节点' },
]

export const MANAGER_LEVEL_OPTIONS: Array<{ value: number; label: string }> = [
  { value: 1, label: '本部门负责人' },
  { value: 2, label: '上级部门负责人' },
  { value: 3, label: '上上级部门负责人' },
  { value: 4, label: '第 4 级部门负责人' },
  { value: 5, label: '第 5 级部门负责人' },
]

export function managerLevelLabel(level: number): string {
  return (
    MANAGER_LEVEL_OPTIONS.find((item) => item.value === level)?.label ??
    `第 ${level} 级部门负责人`
  )
}
