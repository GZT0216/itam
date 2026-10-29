<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Refresh, Search } from '@element-plus/icons-vue'

import { inboundApi } from '@/api/inbound'
import { useFilterMemory } from '@/composables/useFilterMemory'
import type {
  StockAsset,
  StockCategoryOption,
  StockLocation,
  StockOverview,
} from '@/types/inbound'
import { formatDateTime } from '@/utils/format'

const NO_LOCATION_KEY = '__none__'

const overview = ref<StockOverview | null>(null)
const overviewLoading = ref(false)
const loading = ref(false)
const items = ref<StockAsset[]>([])
const total = ref(0)
const categories = ref<StockCategoryOption[]>([])

const query = reactive({
  page: 1,
  page_size: 20,
  keyword: '',
  category_id: undefined as number | undefined,
  include_child: true,
  location: undefined as string | undefined,
})

const filterMemory = useFilterMemory('assets-stock', query, {
  defaults: {
    page: 1,
    page_size: 20,
    keyword: '',
    category_id: undefined,
    include_child: true,
    location: undefined,
  },
})
filterMemory.restore()

const activeLocationLabel = computed(() => {
  if (!query.location) return ''
  if (query.location === NO_LOCATION_KEY) return '未指定位置'
  return query.location
})

const warningShortage = computed(
  () => overview.value?.warnings.reduce((sum, item) => sum + item.shortage, 0) ?? 0,
)

function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return `¥${Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function categoryLabel(category: StockCategoryOption): string {
  return `${'　'.repeat(Math.max(category.level - 1, 0))}${category.name}`
}

function locationKey(location: StockLocation): string {
  return location.location ?? NO_LOCATION_KEY
}

async function loadOverview(): Promise<void> {
  overviewLoading.value = true
  try {
    overview.value = await inboundApi.stockOverview()
  } finally {
    overviewLoading.value = false
  }
}

async function loadItems(): Promise<void> {
  loading.value = true
  try {
    const page = await inboundApi.stockItems({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      category_id: query.category_id,
      include_child: query.include_child,
      location: query.location,
    })
    items.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
}

async function loadCategories(): Promise<void> {
  categories.value = await inboundApi.stockCategories()
}

function handleSearch(): void {
  query.page = 1
  void loadItems()
}

function resetFilters(): void {
  filterMemory.clear()
  query.keyword = ''
  query.category_id = undefined
  query.include_child = true
  query.location = undefined
  query.page = 1
  void loadItems()
}

function selectLocation(location: StockLocation | null): void {
  query.location = location ? locationKey(location) : undefined
  handleSearch()
}

async function refreshAll(): Promise<void> {
  await Promise.all([loadOverview(), loadItems(), loadCategories()])
}

onMounted(refreshAll)
</script>

<template>
  <div class="page stock-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">STOCK OVERVIEW</p>
        <h1 class="page-title">库存管理</h1>
        <p class="page-subtitle">
          实时查看在库资产分布、库存价值与低库存预警。数据直接来源于资产台账，入库、领用、归还后即时同步。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" :loading="loading || overviewLoading" @click="refreshAll">
          刷新
        </el-button>
      </div>
    </header>

    <section class="metric-grid" v-loading="overviewLoading">
      <article class="surface-card metric-card">
        <p class="metric-label">在库资产</p>
        <p class="metric-value">{{ overview?.in_stock_count ?? 0 }}<small>台/件</small></p>
        <p class="metric-hint">状态为「在库」且未删除的资产</p>
      </article>
      <article class="surface-card metric-card">
        <p class="metric-label">库存总值</p>
        <p class="metric-value">{{ money(overview?.in_stock_value) }}</p>
        <p class="metric-hint">按采购价格汇总</p>
      </article>
      <article class="surface-card metric-card">
        <p class="metric-label">存放位置</p>
        <p class="metric-value">{{ overview?.location_count ?? 0 }}<small>处</small></p>
        <p class="metric-hint">含「未指定位置」</p>
      </article>
      <article class="surface-card metric-card" :class="{ 'metric-warning': warningShortage > 0 }">
        <p class="metric-label">低库存预警</p>
        <p class="metric-value">{{ overview?.warning_count ?? 0 }}<small>项</small></p>
        <p class="metric-hint">
          {{ warningShortage > 0 ? `共缺 ${warningShortage} 台/件` : '低于安全库存时触发' }}
        </p>
      </article>
    </section>

    <section class="stock-grid">
      <div class="surface-card panel" v-loading="overviewLoading">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">存放位置分布</h2>
            <p class="panel-subtitle">点击位置可筛选中下方在库明细</p>
          </div>
          <el-button v-if="query.location" text type="primary" @click="selectLocation(null)">
            查看全部
          </el-button>
        </div>
        <div v-if="overview?.locations.length" class="location-list">
          <button
            v-for="location in overview.locations"
            :key="locationKey(location)"
            type="button"
            class="location-card"
            :class="{ active: query.location === locationKey(location) }"
            @click="selectLocation(location)"
          >
            <span class="location-name">{{ location.location_label }}</span>
            <span class="location-count">{{ location.asset_count }} 台/件</span>
            <span class="location-value">{{ money(location.total_value) }}</span>
          </button>
        </div>
        <el-empty v-else description="暂无在库资产" :image-size="64" />
      </div>

      <div class="surface-card panel" v-loading="overviewLoading">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">低库存预警</h2>
            <p class="panel-subtitle">在「资产分类」中配置安全库存后生效</p>
          </div>
          <el-tag v-if="overview?.warning_count" type="danger" effect="light">
            {{ overview.warning_count }} 项
          </el-tag>
        </div>
        <div v-if="overview?.warnings.length" class="warning-list">
          <div
            v-for="warning in overview.warnings"
            :key="warning.category_id"
            class="warning-item"
          >
            <div class="warning-main">
              <span>{{ warning.category_name }}</span>
              <small>安全库存 {{ warning.safety_stock }} · 当前 {{ warning.stock_count }}</small>
            </div>
            <el-tag type="danger" effect="light">缺 {{ warning.shortage }}</el-tag>
          </div>
        </div>
        <el-empty
          v-else
          description="所有已配置安全库存的分类库存充足"
          :image-size="64"
        />
      </div>
    </section>

    <section class="surface-card panel">
      <div class="filter-bar">
        <el-input
          v-model="query.keyword"
          :prefix-icon="Search"
          placeholder="资产编号 / 名称 / 序列号"
          clearable
          class="filter-keyword"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select
          v-model="query.category_id"
          filterable
          clearable
          placeholder="资产分类"
          class="filter-select"
          @change="handleSearch"
        >
          <el-option
            v-for="category in categories"
            :key="category.id"
            :label="categoryLabel(category)"
            :value="category.id"
          />
        </el-select>
        <el-checkbox v-model="query.include_child" @change="handleSearch">含子分类</el-checkbox>
        <div v-if="query.location" class="location-hint">
          <span>位置：{{ activeLocationLabel }}</span>
          <el-button link type="primary" @click="selectLocation(null)">清除</el-button>
        </div>
        <div class="filter-actions">
          <el-button :icon="Search" @click="handleSearch">查询</el-button>
          <el-button text @click="resetFilters">重置</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="items" row-key="id" empty-text="暂无在库资产">
        <el-table-column label="资产" min-width="200">
          <template #default="{ row }">
            <div class="stack-cell">
              <span class="mono">{{ row.asset_no }}</span>
              <small>{{ row.name }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="分类 / 型号" min-width="180">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.category_name || '未分类' }}</span>
              <small>{{ row.model_name || '未指定型号' }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="序列号" min-width="150">
          <template #default="{ row }">{{ row.serial_no || '—' }}</template>
        </el-table-column>
        <el-table-column label="存放位置" min-width="150">
          <template #default="{ row }">{{ row.location || '未指定位置' }}</template>
        </el-table-column>
        <el-table-column label="归属部门" min-width="140">
          <template #default="{ row }">{{ row.dept_name || '未指定部门' }}</template>
        </el-table-column>
        <el-table-column label="采购价格" width="130">
          <template #default="{ row }">{{ money(row.purchase_price) }}</template>
        </el-table-column>
        <el-table-column label="保修截止" width="110">
          <template #default="{ row }">{{ row.warranty_end || '—' }}</template>
        </el-table-column>
        <el-table-column label="入库时间" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="table-footer">
        <el-pagination
          v-model:current-page="query.page"
          v-model:page-size="query.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadItems"
          @size-change="handleSearch"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.page-actions {
  display: flex;
  gap: 10px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.metric-card {
  padding: 18px 20px;
}

.metric-label {
  margin: 0;
  color: var(--text-3);
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.metric-value {
  margin: 8px 0 4px;
  font-family: var(--font-number);
  font-size: 26px;
  font-weight: 700;
  color: var(--text-1);
}

.metric-value small {
  margin-left: 6px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-3);
}

.metric-hint {
  margin: 0;
  color: var(--text-3);
  font-size: 12px;
}

.metric-warning .metric-value {
  color: var(--danger, #d64545);
}

.stock-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.panel {
  padding: 20px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.panel-title {
  margin: 0;
  font-size: 15px;
  font-weight: 650;
  color: var(--text-1);
}

.panel-subtitle {
  margin: 4px 0 0;
  color: var(--text-3);
  font-size: 12px;
}

.location-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.location-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--surface-muted);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.location-card:hover {
  border-color: var(--brand);
}

.location-card.active {
  border-color: var(--brand);
  box-shadow: 0 0 0 2px var(--brand-soft);
}

.location-name {
  font-weight: 650;
  color: var(--text-1);
}

.location-count {
  font-family: var(--font-number);
  font-size: 18px;
  font-weight: 700;
  color: var(--text-1);
}

.location-value {
  color: var(--text-3);
  font-size: 12px;
}

.warning-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 240px;
  overflow-y: auto;
}

.warning-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface-muted);
}

.warning-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.warning-main span {
  font-weight: 600;
  color: var(--text-1);
}

.warning-main small {
  color: var(--text-3);
  font-size: 11.5px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.filter-keyword {
  width: 280px;
}

.filter-select {
  width: 180px;
}

.location-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--text-2);
  font-size: 12px;
}

.filter-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.stack-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stack-cell small {
  color: var(--text-3);
  font-size: 11.5px;
}

.mono {
  font-family: var(--font-number);
  font-weight: 600;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

@media (max-width: 1180px) {
  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .stock-grid {
    grid-template-columns: 1fr;
  }

  .filter-keyword {
    width: 100%;
  }
}
</style>
