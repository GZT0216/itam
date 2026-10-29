import { onBeforeUnmount, watch, type WatchStopHandle } from 'vue'

const STORAGE_PREFIX = 'itam:filters:'

interface FilterMemoryOptions<T extends Record<string, any>> {
  defaults: T
  exclude?: string[]
  debounce?: number
}

function readStored(key: string): Record<string, unknown> | null {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return null
    const parsed = JSON.parse(raw) as unknown
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) return null
    return parsed as Record<string, unknown>
  } catch {
    return null
  }
}

function sameKind(value: unknown, fallback: unknown): boolean {
  if (fallback === undefined || fallback === null) {
    return (
      value === undefined ||
      value === null ||
      typeof value === 'string' ||
      typeof value === 'number' ||
      typeof value === 'boolean'
    )
  }
  return typeof value === typeof fallback
}

/**
 * 将列表筛选条件按页面维度保存到 localStorage，返回页面时自动恢复。
 * 分页默认不恢复，避免记忆到已不存在的页码。
 */
export function useFilterMemory<T extends Record<string, any>>(
  key: string,
  state: T,
  options: FilterMemoryOptions<T>,
) {
  const storageKey = `${STORAGE_PREFIX}${key}`
  const excluded = new Set(options.exclude ?? ['page'])
  const debounce = options.debounce ?? 240
  const keys = Object.keys(options.defaults).filter((field) => !excluded.has(field))

  let timer: ReturnType<typeof setTimeout> | undefined
  let stopHandle: WatchStopHandle | undefined

  function restore(): boolean {
    const stored = readStored(storageKey)
    if (!stored) return false
    let applied = false
    keys.forEach((field) => {
      if (!(field in stored)) return
      const value = stored[field]
      if (!sameKind(value, options.defaults[field])) return
      ;(state as Record<string, unknown>)[field] = value
      applied = true
    })
    return applied
  }

  function persist(): void {
    const payload: Record<string, unknown> = {}
    keys.forEach((field) => {
      const value = state[field]
      if (value !== undefined) payload[field] = value
    })
    try {
      localStorage.setItem(storageKey, JSON.stringify(payload))
    } catch {
      // 存储不可用（隐私模式等）时静默降级
    }
  }

  function clear(): void {
    try {
      localStorage.removeItem(storageKey)
    } catch {
      // 忽略存储异常
    }
  }

  function resetToDefaults(): void {
    keys.forEach((field) => {
      ;(state as Record<string, unknown>)[field] = options.defaults[field]
    })
    clear()
  }

  function start(): void {
    if (stopHandle) return
    stopHandle = watch(
      () => state,
      () => {
        if (timer) clearTimeout(timer)
        timer = setTimeout(persist, debounce)
      },
      { deep: true },
    )
  }

  function stop(): void {
    if (timer) {
      clearTimeout(timer)
      timer = undefined
    }
    stopHandle?.()
    stopHandle = undefined
  }

  onBeforeUnmount(stop)
  start()

  return { restore, clear, resetToDefaults, hasStored: () => readStored(storageKey) !== null }
}
