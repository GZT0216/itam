<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    items: readonly any[]
    itemHeight: number
    height: number
    buffer?: number
  }>(),
  { buffer: 4 },
)

const scroller = ref<HTMLDivElement>()
const scrollTop = ref(0)
const viewport = ref(props.height)
let observer: ResizeObserver | null = null

const startIndex = computed(() =>
  Math.max(0, Math.floor(scrollTop.value / props.itemHeight) - props.buffer),
)
const visibleCount = computed(
  () => Math.ceil(viewport.value / props.itemHeight) + props.buffer * 2,
)
const endIndex = computed(() =>
  Math.min(props.items.length, startIndex.value + visibleCount.value),
)
const visibleItems = computed(() => props.items.slice(startIndex.value, endIndex.value))
const offsetY = computed(() => startIndex.value * props.itemHeight)

function handleScroll(): void {
  scrollTop.value = scroller.value?.scrollTop ?? 0
}

onMounted(() => {
  if (!scroller.value) return
  viewport.value = scroller.value.clientHeight || props.height
  observer = new ResizeObserver(() => {
    if (scroller.value) viewport.value = scroller.value.clientHeight
  })
  observer.observe(scroller.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})
</script>

<template>
  <div ref="scroller" class="virtual-list" :style="{ height: `${height}px` }" @scroll.passive="handleScroll">
    <div class="virtual-list-spacer" :style="{ height: `${items.length * itemHeight}px` }">
      <div class="virtual-list-window" :style="{ transform: `translateY(${offsetY}px)` }">
        <div
          v-for="(item, index) in visibleItems"
          :key="startIndex + index"
          class="virtual-list-item"
          :style="{ height: `${itemHeight}px` }"
        >
          <slot :item="item" :index="startIndex + index" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.virtual-list {
  position: relative;
  overflow-y: auto;
  overscroll-behavior: contain;
}

.virtual-list-spacer {
  position: relative;
  width: 100%;
}

.virtual-list-window {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  will-change: transform;
}

.virtual-list-item {
  box-sizing: border-box;
  overflow: hidden;
}
</style>
