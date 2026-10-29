export type TodoCategory = 'APPROVAL' | 'CONFIRM' | 'HANDLE' | 'MINE' | 'DUE' | string

export interface TodoItem {
  key: string
  category: TodoCategory
  category_label: string
  todo_type: string
  todo_type_label: string
  title: string
  subtitle: string | null
  doc_no: string
  status: string
  status_label: string
  related_name: string | null
  dept_name: string | null
  occurred_at: string | null
  due_date: string | null
  days_to_due: number | null
  is_overdue: boolean
  link: string
}

export interface TodoTypeCount {
  todo_type: string
  label: string
  category: TodoCategory
  count: number
}

export interface TodoCategoryGroup {
  category: TodoCategory
  label: string
  count: number
  types: TodoTypeCount[]
  items: TodoItem[]
}

export interface TodoSummary {
  total: number
  categories: TodoCategoryGroup[]
  generated_at: string
}

export interface TodoPage {
  items: TodoItem[]
  total: number
  page: number
  page_size: number
}
