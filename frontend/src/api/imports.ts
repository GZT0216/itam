import { request } from '@/api/request'
import type { ImportKind, ImportResult } from '@/types/imports'

const TEMPLATE_URLS: Record<ImportKind, string> = {
  users: '/imports/users/template',
  assets: '/imports/assets/template',
  categories: '/imports/asset-categories/template',
}

const IMPORT_URLS: Record<ImportKind, string> = {
  users: '/imports/users',
  assets: '/imports/assets',
  categories: '/imports/asset-categories',
}

export const importApi = {
  downloadTemplate(kind: ImportKind): Promise<Blob> {
    return request<Blob>({
      url: TEMPLATE_URLS[kind],
      responseType: 'blob',
      timeout: 60000,
    })
  },

  run(kind: ImportKind, file: File): Promise<ImportResult> {
    const data = new FormData()
    data.append('file', file)
    return request<ImportResult>({
      url: IMPORT_URLS[kind],
      method: 'post',
      data,
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    })
  },
}
