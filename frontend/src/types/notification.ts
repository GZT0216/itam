export interface NotificationItem {
  id: string
  category: 'asset' | 'ldap' | 'security' | string
  level: 'info' | 'warning' | 'danger' | string
  title: string
  description: string
  occurred_at: string
  link: string | null
}

export interface NotificationSummary {
  items: NotificationItem[]
  total: number
  warning_count: number
  danger_count: number
  generated_at: string
}
