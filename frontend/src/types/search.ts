export type SearchItemType = 'asset' | 'user' | 'dept'

export interface SearchItem {
  type: SearchItemType
  id: number
  title: string
  subtitle: string | null
  keyword: string
}

export interface SearchResult {
  keyword: string
  items: SearchItem[]
}
