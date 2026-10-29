import { request } from '@/api/request'
import type { TodoPage, TodoSummary } from '@/types/todo'

export interface TodoListParams {
  category?: string
  todo_type?: string
  page?: number
  page_size?: number
  sort?: 'asc' | 'desc'
}

export const todoApi = {
  summary(limit = 5): Promise<TodoSummary> {
    return request<TodoSummary>({ url: '/todos/summary', params: { limit } })
  },
  list(params: TodoListParams = {}): Promise<TodoPage> {
    return request<TodoPage>({ url: '/todos', params })
  },
}
