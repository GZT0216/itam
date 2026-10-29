<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppHeader from './AppHeader.vue'
import SidebarMenu from './SidebarMenu.vue'
import { useAppStore } from '@/stores/app'

const appStore = useAppStore()
const route = useRoute()
const router = useRouter()

const isMobile = ref(false)
const mobileOpen = ref(false)
const pageKey = ref(0)
let mediaQuery: MediaQueryList | null = null

const shellClass = computed(() => ({
  'is-collapsed': isMobile.value ? !mobileOpen.value : appStore.sidebarCollapsed,
}))

function syncViewport(event: MediaQueryList | MediaQueryListEvent): void {
  isMobile.value = event.matches
  if (!event.matches) {
    mobileOpen.value = false
  }
}

function handleToggleSidebar(): void {
  if (isMobile.value) {
    mobileOpen.value = !mobileOpen.value
  } else {
    appStore.toggleSidebar()
  }
}

function closeMobileSidebar(): void {
  if (isMobile.value) {
    mobileOpen.value = false
  }
}

function goHome(): void {
  closeMobileSidebar()
  if (route.path !== '/dashboard') {
    void router.push('/dashboard')
  }
}

function refreshPage(): void {
  pageKey.value += 1
}

watch(
  () => route.path,
  () => closeMobileSidebar(),
)

onMounted(() => {
  mediaQuery = window.matchMedia('(max-width: 960px)')
  syncViewport(mediaQuery)
  mediaQuery.addEventListener('change', syncViewport)
})

onBeforeUnmount(() => {
  mediaQuery?.removeEventListener('change', syncViewport)
})
</script>

<template>
  <div class="app-shell" :class="shellClass">
    <aside class="app-sidebar">
      <div class="sidebar-brand" @click="goHome">
        <div class="brand-mark">IT</div>
        <div class="brand-copy">
          <span class="brand-name">ITAM</span>
          <span class="brand-sub">IT ASSET CONTROL</span>
        </div>
      </div>

      <SidebarMenu :collapsed="!isMobile && appStore.sidebarCollapsed" />

      <div class="sidebar-footer">
        <div class="sidebar-status">
          <span class="status-dot" />
          <span>服务运行正常 · v0.1.0</span>
        </div>
      </div>
    </aside>

    <div v-if="isMobile && mobileOpen" class="sidebar-overlay" @click="closeMobileSidebar" />

    <div class="app-main">
      <AppHeader @toggle-sidebar="handleToggleSidebar" @refresh-page="refreshPage" />
      <main class="app-content">
        <RouterView v-slot="{ Component }">
          <Transition name="page-fade-slide" mode="out-in" appear>
            <component :is="Component" :key="`${route.path}-${pageKey}`" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>
