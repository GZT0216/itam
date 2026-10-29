import { onBeforeUnmount, ref, watch } from 'vue'

const STORAGE_PREFIX = 'itam:draft:'
const DEFAULT_TTL = 7 * 24 * 60 * 60 * 1000

interface StoredDraft {
  savedAt: number
  data: Record<string, unknown>
}

interface FormDraftOptions<T> {
  isMeaningful: (form: T) => boolean
  ttlMs?: number
  debounce?: number
}

/**
 * 将未提交的表单内容暂存到 localStorage，再次打开同一表单时恢复。
 * 仅在 active 期间（弹窗打开）自动保存，提交成功后由调用方 clear()。
 */
export function useFormDraft<T extends Record<string, any>>(
  key: string,
  form: T,
  options: FormDraftOptions<T>,
) {
  const storageKey = `${STORAGE_PREFIX}${key}`
  const ttl = options.ttlMs ?? DEFAULT_TTL
  const debounce = options.debounce ?? 500
  const savedAt = ref<number | null>(null)
  let timer: ReturnType<typeof setTimeout> | undefined
  let active = false

  function read(): StoredDraft | null {
    try {
      const raw = localStorage.getItem(storageKey)
      if (!raw) return null
      const parsed = JSON.parse(raw) as StoredDraft
      if (!parsed || typeof parsed !== 'object' || typeof parsed.savedAt !== 'number') return null
      if (Date.now() - parsed.savedAt > ttl) {
        localStorage.removeItem(storageKey)
        return null
      }
      if (!parsed.data || typeof parsed.data !== 'object') return null
      return parsed
    } catch {
      return null
    }
  }

  function persist(): void {
    if (!active) return
    if (!options.isMeaningful(form)) {
      try {
        localStorage.removeItem(storageKey)
      } catch {
        // 忽略存储异常
      }
      return
    }
    try {
      const data = JSON.parse(JSON.stringify(form)) as Record<string, unknown>
      localStorage.setItem(storageKey, JSON.stringify({ savedAt: Date.now(), data }))
    } catch {
      // 忽略存储异常
    }
  }

  function restore(): boolean {
    savedAt.value = null
    const draft = read()
    if (!draft) return false
    Object.assign(form, draft.data)
    savedAt.value = draft.savedAt
    return true
  }

  function start(): void {
    active = true
  }

  function stop(): void {
    active = false
    if (timer) {
      clearTimeout(timer)
      timer = undefined
    }
  }

  function clear(): void {
    stop()
    savedAt.value = null
    try {
      localStorage.removeItem(storageKey)
    } catch {
      // 忽略存储异常
    }
  }

  function discard(): void {
    clear()
  }

  watch(
    () => form,
    () => {
      if (!active) return
      if (timer) clearTimeout(timer)
      timer = setTimeout(persist, debounce)
    },
    { deep: true },
  )

  onBeforeUnmount(() => {
    if (timer) clearTimeout(timer)
  })

  return { restore, start, stop, clear, discard, savedAt, hasDraft: () => savedAt.value !== null }
}
