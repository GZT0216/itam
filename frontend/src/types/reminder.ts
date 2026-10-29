export type ReminderCategory = 'WARRANTY' | 'CONTRACT' | 'BORROW' | 'INVENTORY'
export type ReminderLevel = 'danger' | 'warning' | 'info'

export interface ReminderItem {
  id: string
  category: string
  category_label: string
  level: string
  level_label: string
  title: string
  description: string
  due_date: string | null
  days_left: number | null
  source_no: string | null
  owner: string | null
  link: string
}

export interface ReminderCategorySummary {
  category: string
  label: string
  count: number
  danger_count: number
  warning_count: number
  info_count: number
  link: string
}

export interface ReminderSummary {
  total: number
  danger_count: number
  warning_count: number
  info_count: number
  categories: ReminderCategorySummary[]
  email_enabled: boolean
  generated_at: string
}

export interface ReminderPage {
  items: ReminderItem[]
  total: number
  page: number
  page_size: number
}

export interface ReminderQuery {
  category?: string
  level?: string
  keyword?: string
  page: number
  page_size: number
}

export interface ReminderScanResult {
  warranty: number
  contract: number
  borrow: number
  inventory: number
  total: number
  created: number
  already_scanned: boolean
  email_status: string
  generated_at: string
}
