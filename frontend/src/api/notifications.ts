import { request } from '@/api/request'
import type { NotificationSummary } from '@/types/notification'

export const notificationApi = {
  summary(): Promise<NotificationSummary> {
    return request<NotificationSummary>({ url: '/notifications/summary' })
  },
}
