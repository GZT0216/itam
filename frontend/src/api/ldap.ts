import { request } from '@/api/request'
import type {
  LdapConfig,
  LdapConfigPayload,
  LdapConfigUpdatePayload,
  LdapOptions,
  LdapSyncAccepted,
  LdapSyncLog,
  LdapSyncLogPage,
  LdapTestResult,
} from '@/types/ldap'

export const ldapApi = {
  getConfig(): Promise<LdapConfig> {
    return request<LdapConfig>({ url: '/system/ldap/config' })
  },

  saveConfig(payload: LdapConfigUpdatePayload): Promise<LdapConfig> {
    return request<LdapConfig>({ url: '/system/ldap/config', method: 'put', data: payload })
  },

  testConfig(payload: LdapConfigPayload): Promise<LdapTestResult> {
    return request<LdapTestResult>({ url: '/system/ldap/test', method: 'post', data: payload })
  },

  getOptions(): Promise<LdapOptions> {
    return request<LdapOptions>({ url: '/system/ldap/options' })
  },

  triggerSync(): Promise<LdapSyncAccepted> {
    return request<LdapSyncAccepted>({ url: '/system/ldap/sync', method: 'post' })
  },

  listLogs(params: {
    page: number
    page_size: number
    status?: string
  }): Promise<LdapSyncLogPage> {
    return request<LdapSyncLogPage>({ url: '/system/ldap/logs', params })
  },

  getLog(id: number): Promise<LdapSyncLog> {
    return request<LdapSyncLog>({ url: `/system/ldap/logs/${id}` })
  },
}
