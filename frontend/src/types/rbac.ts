export interface RoleItem {
  id: number
  code: string
  name: string
  description: string | null
  data_scope: string
  data_scope_label: string
  status: number
  sort: number
  is_system: boolean
  version: number
  user_count: number
  menu_count: number
  created_at: string
  updated_at: string
}

export interface RolePage {
  items: RoleItem[]
  total: number
  page: number
  page_size: number
}

export interface RoleBriefOption {
  id: number
  code: string
  name: string
  data_scope: string
}

export interface RoleMember {
  id: number
  username: string
  real_name: string
  dept_name: string | null
  status: number
}

export interface RoleUserOption extends RoleMember {}

export interface FieldPermissionItem {
  resource: string
  field: string
  can_view: boolean
  can_edit: boolean
}

export interface RoleDetail extends RoleItem {
  menu_ids: number[]
  dept_ids: number[]
  field_permissions: FieldPermissionItem[]
  users: RoleMember[]
}

export interface DataScopeOption {
  value: string
  label: string
}

export interface FieldDefinition {
  field: string
  label: string
}

export interface RoleMeta {
  data_scopes: DataScopeOption[]
  field_catalog: Record<string, FieldDefinition[]>
}

export interface AdminMenuNode {
  id: number
  parent_id: number | null
  name: string
  type: 'DIR' | 'MENU' | 'BUTTON' | string
  permission_code: string | null
  path: string | null
  component: string | null
  icon: string | null
  sort: number
  visible: boolean
  status: number
  children: AdminMenuNode[]
}

export interface RoleQuery {
  page: number
  page_size: number
  keyword?: string
  status?: number
}

export interface RoleCreatePayload {
  code: string
  name: string
  description?: string | null
  data_scope: string
  sort: number
  status: number
}

export interface RoleUpdatePayload {
  name: string
  description?: string | null
  sort: number
  status: number
  version: number
}

export interface MenuAssignPayload {
  menu_ids: number[]
  version: number
}

export interface DataScopeAssignPayload {
  data_scope: string
  dept_ids: number[]
  version: number
}

export interface FieldPermissionsAssignPayload {
  permissions: FieldPermissionItem[]
  version: number
}

export interface RoleUsersAssignPayload {
  user_ids: number[]
  version: number
}
