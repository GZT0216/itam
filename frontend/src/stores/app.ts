import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

type ThemeMode = 'light' | 'dark'

const THEME_KEY = 'itam_theme'
const SIDEBAR_KEY = 'itam_sidebar_collapsed'
const MOTION_KEY = 'itam_animations'

function storedTheme(): ThemeMode {
  return localStorage.getItem(THEME_KEY) === 'dark' ? 'dark' : 'light'
}

export const useAppStore = defineStore('app', () => {
  const theme = ref<ThemeMode>(storedTheme())
  const sidebarCollapsed = ref(localStorage.getItem(SIDEBAR_KEY) === '1')
  const animationsEnabled = ref(localStorage.getItem(MOTION_KEY) !== 'off')

  const isDark = computed(() => theme.value === 'dark')

  function applyTheme(): void {
    document.documentElement.classList.toggle('dark', theme.value === 'dark')
    localStorage.setItem(THEME_KEY, theme.value)
    const meta = document.querySelector('meta[name="theme-color"]')
    meta?.setAttribute('content', theme.value === 'dark' ? '#070d18' : '#0b1526')
  }

  function applyMotion(): void {
    document.documentElement.classList.toggle('no-animation', !animationsEnabled.value)
    localStorage.setItem(MOTION_KEY, animationsEnabled.value ? 'on' : 'off')
  }

  function toggleTheme(): void {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    applyTheme()
  }

  function toggleAnimations(): void {
    animationsEnabled.value = !animationsEnabled.value
    applyMotion()
  }

  function setSidebarCollapsed(collapsed: boolean): void {
    sidebarCollapsed.value = collapsed
    localStorage.setItem(SIDEBAR_KEY, collapsed ? '1' : '0')
  }

  function toggleSidebar(): void {
    setSidebarCollapsed(!sidebarCollapsed.value)
  }

  return {
    theme,
    isDark,
    sidebarCollapsed,
    animationsEnabled,
    applyTheme,
    applyMotion,
    toggleTheme,
    toggleAnimations,
    setSidebarCollapsed,
    toggleSidebar,
  }
})
