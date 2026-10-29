export type ImportKind = 'users' | 'assets' | 'categories'

export interface ImportErrorItem {
  row: number
  message: string
}

export interface ImportResult {
  total: number
  success: number
  failed: number
  errors: ImportErrorItem[]
}
