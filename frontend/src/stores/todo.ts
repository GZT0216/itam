import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { todoApi } from '@/api/todo'
import type { TodoSummary } from '@/types/todo'

const REFRESH_EVENT = 'itam:todo-refresh'
const POLL_INTERVAL = 120_000

export const useTodoStore = defineStore('todo', () => {
  const summary = ref<TodoSummary | null>(null)
  const loading = ref(false)
  const loaded = ref(false)

  const total = computed(() => summary.value?.total ?? 0)
  const categories = computed(() => summary.value?.categories ?? [])

  let inflight: Promise<void> | null = null
  let rerun = false
  let started = false
  let timer: ReturnType<typeof setInterval> | undefined

  async function refresh(): Promise<void> {
    if (inflight) {
      rerun = true
      return inflight
    }
    loading.value = true
    inflight = (async () => {
      try {
        summary.value = await todoApi.summary()
        loaded.value = true
      } catch {
        // 角标刷新失败不阻塞页面其他操作
      } finally {
        loading.value = false
        inflight = null
      }
    })()
    await inflight
    if (rerun) {
      rerun = false
      await refresh()
    }
  }

  function handleGlobalRefresh(): void {
    void refresh()
  }

  function handleVisibility(): void {
    if (document.visibilityState === 'visible') {
      void refresh()
    }
  }

  function start(): void {
    if (started) return
    started = true
    window.addEventListener(REFRESH_EVENT, handleGlobalRefresh)
    document.addEventListener('visibilitychange', handleVisibility)
    timer = setInterval(() => {
      if (document.visibilityState === 'visible') {
        void refresh()
      }
    }, POLL_INTERVAL)
    void refresh()
  }

  function stop(): void {
    if (!started) return
    started = false
    window.removeEventListener(REFRESH_EVENT, handleGlobalRefresh)
    document.removeEventListener('visibilitychange', handleVisibility)
    if (timer) {
      clearInterval(timer)
      timer = undefined
    }
  }

  function reset(): void {
    summary.value = null
    loaded.value = false
    rerun = false
  }

  return {
    summary,
    loading,
    loaded,
    total,
    categories,
    refresh,
    start,
    stop,
    reset,
  }
})
