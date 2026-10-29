import { request } from '@/api/request'
import type {
  ReminderPage,
  ReminderQuery,
  ReminderScanResult,
  ReminderSummary,
} from '@/types/reminder'

export const reminderApi = {
  summary(): Promise<ReminderSummary> {
    return request<ReminderSummary>({ url: '/reminders/summary' })
  },

  list(params: ReminderQuery): Promise<ReminderPage> {
    return request<ReminderPage>({ url: '/reminders', params })
  },

  scan(): Promise<ReminderScanResult> {
    return request<ReminderScanResult>({ url: '/reminders/scan', method: 'post' })
  },
}
