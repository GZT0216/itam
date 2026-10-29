import { ref } from 'vue'

const STORAGE_PREFIX = 'itam:columns:'
const MIN_WIDTH = 60

interface TableColumnLike {
  columnKey?: string
  property?: string
  label?: string
}

function readWidths(storageKey: string): Record<string, number> {
  try {
    const raw = localStorage.getItem(storageKey)
    if (!raw) return {}
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return {}
    const result: Record<string, number> = {}
    Object.entries(parsed as Record<string, unknown>).forEach(([key, value]) => {
      if (typeof value === 'number' && Number.isFinite(value) && value >= MIN_WIDTH) {
        result[key] = Math.round(value)
      }
    })
    return result
  } catch {
    return {}
  }
}

/**
 * 记忆表格列宽：拖拽表头分隔线后按 column-key 保存，再次进入页面自动应用。
 */
export function useColumnWidths(key: string) {
  const storageKey = `${STORAGE_PREFIX}${key}`
  const widths = ref<Record<string, number>>(readWidths(storageKey))

  function widthOf(columnKey: string): number | undefined {
    return widths.value[columnKey]
  }

  function hasSaved(): boolean {
    return Object.keys(widths.value).length > 0
  }

  function onHeaderDragend(newWidth: number, _oldWidth: number, column: TableColumnLike): void {
    const columnKey = column.columnKey || column.property
    if (!columnKey || !Number.isFinite(newWidth)) return
    const next = { ...widths.value, [columnKey]: Math.max(MIN_WIDTH, Math.round(newWidth)) }
    widths.value = next
    try {
      localStorage.setItem(storageKey, JSON.stringify(next))
    } catch {
      // 存储不可用时仅当前会话生效
    }
  }

  function reset(): void {
    widths.value = {}
    try {
      localStorage.removeItem(storageKey)
    } catch {
      // 忽略存储异常
    }
  }

  return { widthOf, onHeaderDragend, reset, hasSaved }
}
