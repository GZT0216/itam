export type LdapSyncStatus = 'RUNNING' | 'SUCCESS' | 'PARTIAL' | 'FAILED'

export interface LdapConfig {
  id: number
  enabled: boolean
  server_host: string
  server_port: number
  use_ssl: boolean
  start_tls: boolean
  base_dn: string
  bind_dn: string
  has_password: boolean
  user_filter: string
  dept_filter: string
  username_attribute: string
  real_name_attribute: string
  email_attribute: string
  phone_attribute: string
  employee_no_attribute: string
  default_role_id: number | null
  default_role_name: string | null
  root_dept_id: number | null
  root_dept_name: string | null
  sync_interval_minutes: number
  last_sync_at: string | null
  last_sync_status: LdapSyncStatus | null
  last_sync_message: string | null
  last_test_at: string | null
  last_test_status: 'SUCCESS' | 'FAILED' | null
  last_test_message: string | null
  version: number
  created_at: string | null
  updated_at: string | null
}

export interface LdapConfigPayload {
  enabled: boolean
  server_host: string
  server_port: number
  use_ssl: boolean
  start_tls: boolean
  base_dn: string
  bind_dn: string
  bind_password?: string | null
  user_filter: string
  dept_filter: string
  username_attribute: string
  real_name_attribute: string
  email_attribute: string
  phone_attribute: string
  employee_no_attribute: string
  default_role_id: number | null
  root_dept_id: number | null
  sync_interval_minutes: number
}

export interface LdapConfigUpdatePayload extends LdapConfigPayload {
  version?: number
}

export interface LdapTestResult {
  success: boolean
  message: string
  server: string | null
  dept_sample: number
  user_sample: number
  elapsed_ms: number
  checked_at: string
}

export interface LdapSyncLog {
  id: number
  trigger_type: 'MANUAL' | 'SCHEDULED' | string
  status: LdapSyncStatus
  started_at: string
  finished_at: string | null
  duration_ms: number
  dept_total: number
  dept_created: number
  dept_updated: number
  user_total: number
  user_created: number
  user_updated: number
  user_disabled: number
  user_skipped: number
  error_count: number
  operator_name: string | null
  message: string | null
  details: Array<{ level: string; message: string }> | null
  error_message: string | null
}

export interface LdapSyncLogPage {
  items: LdapSyncLog[]
  total: number
  page: number
  page_size: number
}

export interface LdapRoleOption {
  id: number
  code: string
  name: string
}

export interface LdapDeptOption {
  id: number
  parent_id: number | null
  name: string
  level: number
  status: number
}

export interface LdapOptions {
  roles: LdapRoleOption[]
  depts: LdapDeptOption[]
  ldap_dept_count: number
  ldap_user_count: number
  local_user_count: number
}

export interface LdapSyncAccepted {
  accepted: boolean
  config_id: number
  trigger_type: string
}
