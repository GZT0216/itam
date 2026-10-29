import { request } from '@/api/request'
import type { SearchResult } from '@/types/search'

export const searchApi = {
  global(keyword: string, limit = 5): Promise<SearchResult> {
    return request<SearchResult>({
      url: '/search',
      params: { keyword, limit },
      timeout: 15000,
    })
  },
}
