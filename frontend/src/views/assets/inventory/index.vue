<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Document, Download, Plus, Refresh, Search } from '@element-plus/icons-vue'

import { assetOpsApi } from '@/api/assetOps'
import { useAuthStore } from '@/stores/auth'
import type {
  CategoryOption,
  DeptOption,
  InventoryItem,
  InventoryReport,
  InventoryResult,
  InventoryStatus,
  InventorySurplusItem,
  InventoryTaskItem,
} from '@/types/assetOps'
import {
  INVENTORY_RESULT_LABELS,
  INVENTORY_STATUS_LABELS,
} from '@/types/assetOps'
import { formatDateTime } from '@/utils/format'

const auth = useAuthStore()
const route = useRoute()
const focusId = (() => {
  const raw = route.query.focus
  const value = typeof raw === 'string' ? Number(raw) : Number.NaN
  return Number.isInteger(value) && value > 0 ? value : null
})()

const loading = ref(false)
const tasks = ref<InventoryTaskItem[]>([])
const total = ref(0)
const query = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  status: undefined as InventoryStatus | undefined,
})
const statusOptions = Object.entries(INVENTORY_STATUS_LABELS) as Array<
  [InventoryStatus, string]
>

const createVisible = ref(false)
const createSubmitting = ref(false)
const depts = ref<DeptOption[]>([])
const categories = ref<CategoryOption[]>([])
const createForm = reactive({
  name: '',
  scope_dept_id: undefined as number | undefined,
  include_child: true,
  scope_category_id: undefined as number | undefined,
  include_child_category: true,
  planned_date: '',
  remark: '',
})

const detailVisible = ref(false)
const detailTask = ref<InventoryTaskItem | null>(null)
const detailLoading = ref(false)
const items = ref<InventoryItem[]>([])
const itemTotal = ref(0)
const itemQuery = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  result: undefined as InventoryResult | undefined,
})
const resultOptions = Object.entries(INVENTORY_RESULT_LABELS) as Array<
  [InventoryResult, string]
>

const scanCode = ref('')
const scanLoading = ref(false)
const scanInputRef = ref<{ focus: () => void } | null>(null)

const itemDialogVisible = ref(false)
const editingItem = ref<InventoryItem | null>(null)
const itemSubmitting = ref(false)
const itemForm = reactive({
  result: 'NORMAL' as Exclude<InventoryResult, 'PENDING'>,
  actual_location: '',
  remark: '',
})

const surplusItems = ref<InventorySurplusItem[]>([])
const surplusVisible = ref(false)
const surplusSubmitting = ref(false)
const surplusForm = reactive({
  asset_no: '',
  name: '',
  category_id: undefined as number | undefined,
  dept_id: undefined as number | undefined,
  serial_no: '',
  location: '',
  purchase_date: '',
  purchase_price: undefined as number | undefined,
  remark: '',
})

const adjustmentVisible = ref(false)
const adjustmentSubmitting = ref(false)
const adjustmentReason = ref('')

const approveVisible = ref(false)
const approveMode = ref<'approve' | 'reject'>('approve')
const approveComment = ref('')
const approveSubmitting = ref(false)

const reportVisible = ref(false)
const reportLoading = ref(false)
const reportData = ref<InventoryReport | null>(null)
const exporting = ref(false)

const canCreate = computed(() => auth.hasPerm('asset:inventory:create'))
const leafCategories = computed(() => {
  const parents = new Set(
    categories.value
      .map((item) => item.parent_id)
      .filter((value): value is number => value !== null),
  )
  return categories.value.filter((item) => !parents.has(item.id))
})

function progressOf(task: InventoryTaskItem): number {
  if (!task.total_assets) return 0
  return Math.round((task.checked_assets / task.total_assets) * 100)
}

async function fetchTasks(): Promise<void> {
  loading.value = true
  try {
    const page = await assetOpsApi.listInventoryTasks({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      status: query.status,
    })
    tasks.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  query.page = 1
  void fetchTasks()
}

function resetFilters(): void {
  query.keyword = ''
  query.status = undefined
  query.page = 1
  void fetchTasks()
}

async function loadOptions(): Promise<void> {
  const [deptList, categoryList] = await Promise.all([
    depts.value.length ? Promise.resolve(depts.value) : assetOpsApi.departments(),
    categories.value.length ? Promise.resolve(categories.value) : assetOpsApi.categories(),
  ])
  depts.value = deptList
  categories.value = categoryList
}

async function openCreate(): Promise<void> {
  createForm.name = ''
  createForm.scope_dept_id = undefined
  createForm.include_child = true
  createForm.scope_category_id = undefined
  createForm.include_child_category = true
  createForm.planned_date = ''
  createForm.remark = ''
  createVisible.value = true
  await loadOptions()
}

async function submitCreate(): Promise<void> {
  if (createForm.name.trim().length < 2) {
    ElMessage.warning('请填写盘点任务名称（至少 2 个字）')
    return
  }
  createSubmitting.value = true
  try {
    await assetOpsApi.createInventoryTask({
      name: createForm.name.trim(),
      scope_dept_id: createForm.scope_dept_id ?? null,
      include_child: createForm.include_child,
      scope_category_id: createForm.scope_category_id ?? null,
      include_child_category: createForm.include_child_category,
      planned_date: createForm.planned_date || null,
      remark: createForm.remark.trim() || null,
    })
    ElMessage.success('盘点任务已创建，可在详情中扫码或逐项核对')
    createVisible.value = false
    handleSearch()
  } finally {
    createSubmitting.value = false
  }
}

async function openDetail(task: InventoryTaskItem): Promise<void> {
  detailVisible.value = true
  detailTask.value = task
  itemQuery.page = 1
  itemQuery.keyword = ''
  itemQuery.result = undefined
  scanCode.value = ''
  await Promise.all([refreshDetail(), fetchItems(), fetchSurplus()])
  await nextTick()
  scanInputRef.value?.focus()
}

async function openFocused(): Promise<void> {
  if (!focusId) return
  const task = tasks.value.find((item) => item.id === focusId)
  if (task) {
    await openDetail(task)
    return
  }
  try {
    const detail = await assetOpsApi.getInventoryTask(focusId)
    await openDetail(detail)
  } catch {
    // 目标盘点任务无权限或已失效时停留在列表页
  }
}

async function refreshDetail(): Promise<void> {
  if (!detailTask.value) return
  detailLoading.value = true
  try {
    detailTask.value = await assetOpsApi.getInventoryTask(detailTask.value.id)
  } finally {
    detailLoading.value = false
  }
}

async function fetchItems(): Promise<void> {
  if (!detailTask.value) return
  const page = await assetOpsApi.listInventoryItems(detailTask.value.id, {
    page: itemQuery.page,
    page_size: itemQuery.page_size,
    keyword: itemQuery.keyword || undefined,
    result: itemQuery.result,
  })
  items.value = page.items
  itemTotal.value = page.total
}

function handleItemSearch(): void {
  itemQuery.page = 1
  void fetchItems()
}

async function fetchSurplus(): Promise<void> {
  if (!detailTask.value) return
  surplusItems.value = await assetOpsApi.listInventorySurplus(detailTask.value.id)
}

async function openSurplus(): Promise<void> {
  await loadOptions()
  surplusForm.asset_no = ''
  surplusForm.name = ''
  surplusForm.category_id = undefined
  surplusForm.dept_id = detailTask.value?.scope_dept_id ?? undefined
  surplusForm.serial_no = ''
  surplusForm.location = ''
  surplusForm.purchase_date = ''
  surplusForm.purchase_price = undefined
  surplusForm.remark = ''
  surplusVisible.value = true
}

async function submitSurplus(): Promise<void> {
  const task = detailTask.value
  if (!task) return
  if (!surplusForm.asset_no.trim() || !surplusForm.name.trim()) {
    ElMessage.warning('请填写盘盈资产编号与名称')
    return
  }
  if (!surplusForm.category_id) {
    ElMessage.warning('请选择盘盈资产分类')
    return
  }
  surplusSubmitting.value = true
  try {
    await assetOpsApi.addInventorySurplus(task.id, {
      asset_no: surplusForm.asset_no.trim(),
      name: surplusForm.name.trim(),
      category_id: surplusForm.category_id,
      dept_id: surplusForm.dept_id ?? null,
      serial_no: surplusForm.serial_no.trim() || null,
      location: surplusForm.location.trim() || null,
      purchase_date: surplusForm.purchase_date || null,
      purchase_price: surplusForm.purchase_price ?? null,
      remark: surplusForm.remark.trim() || null,
    })
    ElMessage.success('盘盈资产已登记')
    surplusVisible.value = false
    await Promise.all([fetchSurplus(), refreshDetail()])
    await fetchTasks()
  } finally {
    surplusSubmitting.value = false
  }
}

async function removeSurplus(row: InventorySurplusItem): Promise<void> {
  const task = detailTask.value
  if (!task) return
  await ElMessageBox.confirm(
    `确定删除盘盈登记「${row.asset_no} ${row.name}」吗？`,
    '删除盘盈登记',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '返回' },
  )
  await assetOpsApi.deleteInventorySurplus(task.id, row.id)
  ElMessage.success('盘盈登记已删除')
  await Promise.all([fetchSurplus(), refreshDetail()])
}

function openAdjustment(): void {
  adjustmentReason.value = ''
  adjustmentVisible.value = true
}

async function submitAdjustment(): Promise<void> {
  const task = detailTask.value
  if (!task) return
  adjustmentSubmitting.value = true
  try {
    await assetOpsApi.submitInventoryAdjustment(
      task.id,
      adjustmentReason.value.trim() || null,
    )
    ElMessage.success('盘盈盘亏处理已提交审批')
    adjustmentVisible.value = false
    await refreshDetail()
    await fetchTasks()
  } finally {
    adjustmentSubmitting.value = false
  }
}

function openApprove(mode: 'approve' | 'reject'): void {
  approveMode.value = mode
  approveComment.value = ''
  approveVisible.value = true
}

async function submitApprove(): Promise<void> {
  const task = detailTask.value
  if (!task?.adjustment_id) return
  if (approveMode.value === 'reject' && !approveComment.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  approveSubmitting.value = true
  try {
    if (approveMode.value === 'approve') {
      await assetOpsApi.approveInventoryAdjustment(task.id, {
        version: task.adjustment_version ?? 1,
        comment: approveComment.value.trim() || null,
      })
      ElMessage.success('盘点盈亏处理已通过，盘亏资产已核销、盘盈资产已建档')
    } else {
      await assetOpsApi.rejectInventoryAdjustment(task.id, {
        version: task.adjustment_version ?? 1,
        comment: approveComment.value.trim(),
      })
      ElMessage.success('盘点盈亏处理已驳回')
    }
    approveVisible.value = false
    await Promise.all([refreshDetail(), fetchSurplus(), fetchItems()])
    await fetchTasks()
  } finally {
    approveSubmitting.value = false
  }
}

async function openReport(): Promise<void> {
  const task = detailTask.value
  if (!task) return
  reportVisible.value = true
  reportLoading.value = true
  reportData.value = null
  try {
    reportData.value = await assetOpsApi.getInventoryReport(task.id)
  } finally {
    reportLoading.value = false
  }
}

async function exportReport(): Promise<void> {
  const task = detailTask.value
  if (!task) return
  exporting.value = true
  try {
    const blob = await assetOpsApi.exportInventoryReport(task.id)
    if (blob.type.includes('application/json')) {
      const body = JSON.parse(await blob.text()) as { message?: string }
      ElMessage.error(body.message || '导出失败')
      return
    }
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `盘点报告_${task.task_no}.xlsx`
    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } finally {
    exporting.value = false
  }
}

async function submitScan(): Promise<void> {
  const task = detailTask.value
  if (!task || !scanCode.value.trim()) return
  scanLoading.value = true
  try {
    const item = await assetOpsApi.scanInventoryItem(task.id, {
      code: scanCode.value.trim(),
      result: 'NORMAL',
    })
    ElMessage.success(`扫码盘点成功：${item.asset_no} ${item.asset_name}`)
    scanCode.value = ''
    await Promise.all([fetchItems(), refreshDetail()])
    await fetchTasks()
    scanInputRef.value?.focus()
  } finally {
    scanLoading.value = false
  }
}

function openItemDialog(item: InventoryItem): void {
  editingItem.value = item
  itemForm.result = item.result === 'PENDING' ? 'NORMAL' : item.result
  itemForm.actual_location = item.actual_location || item.location || ''
  itemForm.remark = item.remark || ''
  itemDialogVisible.value = true
}

async function submitItem(): Promise<void> {
  const task = detailTask.value
  const item = editingItem.value
  if (!task || !item) return
  itemSubmitting.value = true
  try {
    await assetOpsApi.updateInventoryItem(task.id, item.id, {
      result: itemForm.result,
      actual_location: itemForm.actual_location.trim() || null,
      remark: itemForm.remark.trim() || null,
    })
    ElMessage.success('盘点结果已保存')
    itemDialogVisible.value = false
    await Promise.all([fetchItems(), refreshDetail()])
    await fetchTasks()
  } finally {
    itemSubmitting.value = false
  }
}

async function completeTask(task: InventoryTaskItem): Promise<void> {
  await ElMessageBox.confirm(
    `确定完成盘点任务「${task.name}」吗？完成后不可继续核对。`,
    '完成盘点',
    { type: 'warning', confirmButtonText: '完成盘点', cancelButtonText: '返回' },
  )
  await assetOpsApi.completeInventoryTask(task.id)
  ElMessage.success('盘点任务已完成')
  detailVisible.value = false
  await fetchTasks()
}

async function cancelTask(task: InventoryTaskItem): Promise<void> {
  const { value } = await ElMessageBox.prompt(
    '取消后盘点任务将停止，已录入的核对结果会保留。可填写取消原因。',
    '取消盘点任务',
    {
      confirmButtonText: '确认取消',
      cancelButtonText: '返回',
      inputPlaceholder: '取消原因（选填）',
      inputType: 'textarea',
    },
  )
  await assetOpsApi.cancelInventoryTask(task.id, value?.trim() || null)
  ElMessage.success('盘点任务已取消')
  detailVisible.value = false
  await fetchTasks()
}

function deptLabel(dept: DeptOption): string {
  return `${'　'.repeat(Math.max(dept.level - 1, 0))}${dept.name}`
}

function categoryLabel(category: CategoryOption): string {
  return `${'　'.repeat(Math.max(category.level - 1, 0))}${category.name}`
}

onMounted(async () => {
  const keyword = route.query.keyword
  if (typeof keyword === 'string' && keyword.trim()) {
    query.keyword = keyword.trim()
  }
  await fetchTasks()
  await openFocused()
})
</script>

<template>
  <div class="page inventory-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">ASSET INVENTORY</p>
        <h1 class="page-title">资产盘点</h1>
        <p class="page-subtitle">
          按部门与分类创建盘点任务，支持扫码枪快速核对。盘点只记录实盘结果，不会擅自变更资产状态。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" :loading="loading" @click="fetchTasks">刷新</el-button>
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">
          创建盘点任务
        </el-button>
      </div>
    </header>

    <section class="surface-card panel">
      <div class="filter-bar">
        <el-input
          v-model="query.keyword"
          :prefix-icon="Search"
          placeholder="任务编号 / 任务名称"
          clearable
          class="filter-keyword"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select
          v-model="query.status"
          placeholder="任务状态"
          clearable
          class="filter-select"
          @change="handleSearch"
        >
          <el-option
            v-for="[value, label] in statusOptions"
            :key="value"
            :label="label"
            :value="value"
          />
        </el-select>
        <div class="filter-actions">
          <el-button :icon="Search" @click="handleSearch">查询</el-button>
          <el-button text @click="resetFilters">重置</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="tasks" row-key="id" empty-text="当前没有盘点任务">
        <el-table-column label="盘点任务" min-width="220">
          <template #default="{ row }">
            <div class="stack-cell">
              <span class="task-name">{{ row.name }}</span>
              <small class="mono">{{ row.task_no }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="盘点范围" min-width="200">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>
                {{ row.scope_dept_name || '全部部门' }}
                <template v-if="row.scope_dept_name && row.include_child">
                  （含下级）
                </template>
              </span>
              <small>
                {{ row.scope_category_name || '全部分类' }}
                <template v-if="row.scope_category_name && row.include_child_category">
                  （含子分类）
                </template>
              </small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="盘点进度" min-width="220">
          <template #default="{ row }">
            <el-progress
              :percentage="progressOf(row)"
              :status="row.pending_count === 0 ? 'success' : undefined"
              :stroke-width="10"
            />
            <small class="progress-text">
              已盘 {{ row.checked_assets }} / {{ row.total_assets }} · 正常
              {{ row.normal_count }} · 异常 {{ row.abnormal_count }} · 盘亏
              {{ row.missing_count }} · 盘盈 {{ row.surplus_count }}
            </small>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <div class="stack-cell">
              <el-tag :type="row.status_tag_type" effect="light">
                {{ row.status_label }}
              </el-tag>
              <el-tag
                v-if="row.adjustment_status"
                :type="row.adjustment_status_tag_type || 'info'"
                effect="plain"
                size="small"
              >
                {{ row.adjustment_status_label }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="创建人" min-width="150">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.created_by_name || '—' }}</span>
              <small>{{ formatDateTime(row.created_at) }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">
              {{ row.can_manage ? '继续盘点' : '详情' }}
            </el-button>
            <el-button v-if="row.can_manage" link type="success" @click="completeTask(row)">
              完成
            </el-button>
            <el-button v-if="row.can_manage" link type="warning" @click="cancelTask(row)">
              取消
            </el-button>
          </template>
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
          @current-change="fetchTasks"
          @size-change="handleSearch"
        />
      </div>
    </section>

    <el-dialog v-model="createVisible" title="创建盘点任务" width="600px">
      <el-form label-position="top">
        <el-form-item label="任务名称" required>
          <el-input
            v-model="createForm.name"
            maxlength="120"
            placeholder="如：2026 年第四季度 IT 部资产盘点"
          />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="盘点部门">
            <el-select
              v-model="createForm.scope_dept_id"
              clearable
              filterable
              placeholder="不选则按数据范围全部部门"
              class="full-width"
            >
              <el-option
                v-for="dept in depts"
                :key="dept.id"
                :label="deptLabel(dept)"
                :value="dept.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="包含下级部门">
            <el-switch
              v-model="createForm.include_child"
              :disabled="!createForm.scope_dept_id"
            />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="资产分类">
            <el-select
              v-model="createForm.scope_category_id"
              clearable
              filterable
              placeholder="不选则包含全部分类"
              class="full-width"
            >
              <el-option
                v-for="category in categories"
                :key="category.id"
                :label="categoryLabel(category)"
                :value="category.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="包含子分类">
            <el-switch
              v-model="createForm.include_child_category"
              :disabled="!createForm.scope_category_id"
            />
          </el-form-item>
        </div>
        <el-form-item label="计划盘点日期">
          <el-date-picker
            v-model="createForm.planned_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择日期"
            class="full-width"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="createForm.remark"
            type="textarea"
            :rows="2"
            maxlength="500"
            show-word-limit
            placeholder="盘点要求或注意事项（选填）"
          />
        </el-form-item>
      </el-form>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="创建时会自动快照盘点范围内的资产；已在其他进行中盘点任务内的资产会被跳过"
      />
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSubmitting" @click="submitCreate">
          创建任务
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" size="76%" :with-header="false">
      <div v-if="detailTask" v-loading="detailLoading" class="inventory-detail">
        <header class="detail-head">
          <div>
            <p class="page-eyebrow">INVENTORY TASK</p>
            <h2 class="detail-title">{{ detailTask.name }}</h2>
            <p class="detail-subtitle">
              <span class="mono">{{ detailTask.task_no }}</span>
              · {{ detailTask.scope_dept_name || '全部部门' }}
              · {{ detailTask.scope_category_name || '全部分类' }}
              · 创建人 {{ detailTask.created_by_name || '—' }}
            </p>
          </div>
          <div class="detail-head-actions">
            <el-tag :type="detailTask.status_tag_type" effect="light">
              {{ detailTask.status_label }}
            </el-tag>
            <el-button :icon="Document" @click="openReport">盘点报告</el-button>
            <el-button
              v-if="detailTask.can_submit_adjustment"
              type="primary"
              @click="openAdjustment"
            >
              提交盈亏处理
            </el-button>
            <template v-if="detailTask.can_approve_adjustment">
              <el-button type="success" @click="openApprove('approve')">
                通过处理
              </el-button>
              <el-button type="danger" plain @click="openApprove('reject')">
                驳回
              </el-button>
            </template>
            <el-button
              v-if="detailTask.can_manage"
              type="success"
              @click="completeTask(detailTask)"
            >
              完成盘点
            </el-button>
            <el-button
              v-if="detailTask.can_manage"
              type="warning"
              plain
              @click="cancelTask(detailTask)"
            >
              取消任务
            </el-button>
            <el-button @click="detailVisible = false">关闭</el-button>
          </div>
        </header>

        <section class="detail-stats">
          <div class="stat-card">
            <span>资产总数</span>
            <strong>{{ detailTask.total_assets }}</strong>
          </div>
          <div class="stat-card">
            <span>已盘点</span>
            <strong>{{ detailTask.checked_assets }}</strong>
          </div>
          <div class="stat-card tone-success">
            <span>正常</span>
            <strong>{{ detailTask.normal_count }}</strong>
          </div>
          <div class="stat-card tone-warning">
            <span>异常</span>
            <strong>{{ detailTask.abnormal_count }}</strong>
          </div>
          <div class="stat-card tone-danger">
            <span>盘亏</span>
            <strong>{{ detailTask.missing_count }}</strong>
          </div>
          <div class="stat-card tone-brand">
            <span>盘盈</span>
            <strong>{{ detailTask.surplus_count }}</strong>
          </div>
          <div class="stat-card">
            <span>待核对</span>
            <strong>{{ detailTask.pending_count }}</strong>
          </div>
        </section>

        <el-progress
          :percentage="progressOf(detailTask)"
          :status="detailTask.pending_count === 0 ? 'success' : undefined"
          :stroke-width="12"
          class="detail-progress"
        />

        <section v-if="detailTask.can_manage" class="scan-panel">
          <div class="scan-copy">
            <strong>扫码盘点</strong>
            <span>扫码枪扫描或手动输入资产编号后回车，默认标记为「正常」</span>
          </div>
          <div class="scan-input">
            <el-input
              ref="scanInputRef"
              v-model="scanCode"
              size="large"
              placeholder="扫描 / 输入资产编号"
              clearable
              @keyup.enter="submitScan"
            />
            <el-button
              type="primary"
              size="large"
              :loading="scanLoading"
              @click="submitScan"
            >
              核对录入
            </el-button>
          </div>
        </section>

        <section class="surface-card detail-panel surplus-panel">
          <div class="section-head">
            <div>
              <strong>盘盈资产</strong>
              <small>
                盘点中发现的未入账资产；提交盈亏处理并通过审批后，将自动创建资产档案
              </small>
            </div>
            <el-button
              v-if="detailTask.can_manage"
              size="small"
              type="primary"
              plain
              :icon="Plus"
              @click="openSurplus"
            >
              登记盘盈
            </el-button>
          </div>
          <el-table
            :data="surplusItems"
            row-key="id"
            size="small"
            empty-text="暂无盘盈登记"
          >
            <el-table-column label="盘盈资产" min-width="190">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.name }}</span>
                  <small class="mono">{{ row.asset_no }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="分类 / 部门" min-width="170">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.category_name || '未分类' }}</span>
                  <small>{{ row.dept_name || '未分配部门' }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="序列号 / 位置" min-width="180">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.serial_no || '—' }}</span>
                  <small>{{ row.location || '未登记位置' }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="购入信息" min-width="150">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.purchase_date || '—' }}</span>
                  <small>
                    {{ row.purchase_price != null ? `¥${row.purchase_price}` : '未登记金额' }}
                  </small>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="处理状态" width="110">
              <template #default="{ row }">
                <el-tag
                  :type="row.applied_at ? 'success' : 'warning'"
                  effect="light"
                  size="small"
                >
                  {{ row.applied_at ? '已建档' : '待处理' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="detailTask.can_manage && !row.applied_at"
                  link
                  type="danger"
                  :icon="Delete"
                  @click="removeSurplus(row)"
                >
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </section>

        <section
          v-if="detailTask.adjustment_id"
          class="surface-card detail-panel adjustment-panel"
        >
          <div class="section-head">
            <div>
              <strong>盈亏处理单</strong>
              <small>
                {{ detailTask.adjustment_no }} · 盘亏 {{ detailTask.missing_count }} 项 ·
                盘盈 {{ detailTask.surplus_count }} 项
              </small>
            </div>
            <el-tag
              :type="detailTask.adjustment_status_tag_type || 'info'"
              effect="light"
            >
              {{ detailTask.adjustment_status_label }}
            </el-tag>
          </div>
          <el-alert
            v-if="detailTask.adjustment_status === 'PENDING'"
            type="warning"
            :closable="false"
            show-icon
            title="盈亏处理待审批，审批通过后才会核销盘亏资产并创建盘盈资产档案"
          />
          <el-alert
            v-else-if="detailTask.adjustment_status === 'REJECTED'"
            type="error"
            :closable="false"
            show-icon
            title="盈亏处理已被驳回，可调整盘盈登记后重新提交"
          />
          <el-alert
            v-else
            type="success"
            :closable="false"
            show-icon
            title="盈亏处理已通过，盘亏资产已核销，盘盈资产已建档"
          />
        </section>

        <section class="surface-card detail-panel">
          <div class="filter-bar">
            <el-input
              v-model="itemQuery.keyword"
              :prefix-icon="Search"
              placeholder="资产编号 / 名称 / 责任人"
              clearable
              class="filter-keyword"
              @keyup.enter="handleItemSearch"
              @clear="handleItemSearch"
            />
            <el-select
              v-model="itemQuery.result"
              placeholder="盘点结果"
              clearable
              class="filter-select"
              @change="handleItemSearch"
            >
              <el-option
                v-for="[value, label] in resultOptions"
                :key="value"
                :label="label"
                :value="value"
              />
            </el-select>
            <div class="filter-actions">
              <el-button :icon="Search" @click="handleItemSearch">查询</el-button>
            </div>
          </div>

          <el-table :data="items" row-key="id" empty-text="没有匹配的盘点明细">
            <el-table-column label="资产" min-width="210">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.asset_name }}</span>
                  <small class="mono">{{ row.asset_no }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="分类 / 部门" min-width="170">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.category_name || '未分类' }}</span>
                  <small>{{ row.dept_name || '未分配部门' }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="账面信息" min-width="170">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.location || '未登记位置' }}</span>
                  <small>{{ row.custodian_name || '无责任人' }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="实盘结果" width="130">
              <template #default="{ row }">
                <el-tag :type="row.result_tag_type" effect="light">
                  {{ row.result_label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="实盘信息" min-width="190">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.actual_location || '—' }}</span>
                  <small>{{ row.remark || row.checked_by_name || '尚未核对' }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="核对时间" width="150">
              <template #default="{ row }">
                {{ formatDateTime(row.checked_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button
                  link
                  type="primary"
                  :disabled="!detailTask?.can_manage"
                  @click="openItemDialog(row)"
                >
                  核对
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="table-footer">
            <el-pagination
              v-model:current-page="itemQuery.page"
              v-model:page-size="itemQuery.page_size"
              :total="itemTotal"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              background
              @current-change="fetchItems"
              @size-change="handleItemSearch"
            />
          </div>
        </section>
      </div>
    </el-drawer>

    <el-dialog v-model="itemDialogVisible" title="盘点核对" width="480px">
      <div v-if="editingItem" class="action-summary">
        <div>
          <span>{{ editingItem.asset_name }}</span>
          <small>
            {{ editingItem.asset_no }} · 账面位置
            {{ editingItem.location || '未登记' }}
          </small>
        </div>
        <el-tag :type="editingItem.result_tag_type" effect="light">
          {{ editingItem.result_label }}
        </el-tag>
      </div>
      <el-form label-position="top">
        <el-form-item label="盘点结果" required>
          <el-radio-group v-model="itemForm.result">
            <el-radio-button value="NORMAL">正常</el-radio-button>
            <el-radio-button value="ABNORMAL">异常</el-radio-button>
            <el-radio-button value="MISSING">盘亏</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="实际位置">
          <el-input
            v-model="itemForm.actual_location"
            maxlength="120"
            placeholder="现场实际存放位置"
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="itemForm.remark"
            type="textarea"
            :rows="2"
            maxlength="500"
            show-word-limit
            placeholder="异常情况或盘亏说明（选填）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="itemDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="itemSubmitting" @click="submitItem">
          保存盘点结果
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="surplusVisible" title="登记盘盈资产" width="580px">
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="资产编号" required>
            <el-input
              v-model="surplusForm.asset_no"
              maxlength="50"
              placeholder="盘盈资产的实际编号"
            />
          </el-form-item>
          <el-form-item label="资产名称" required>
            <el-input v-model="surplusForm.name" maxlength="120" placeholder="如：笔记本电脑" />
          </el-form-item>
        </div>
        <el-form-item label="资产分类" required>
          <el-select
            v-model="surplusForm.category_id"
            filterable
            placeholder="请选择最终一级分类"
            class="full-width"
          >
            <el-option
              v-for="category in leafCategories"
              :key="category.id"
              :label="categoryLabel(category)"
              :value="category.id"
            />
          </el-select>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="所属部门">
            <el-select
              v-model="surplusForm.dept_id"
              clearable
              filterable
              placeholder="默认盘点部门"
              class="full-width"
            >
              <el-option
                v-for="dept in depts"
                :key="dept.id"
                :label="deptLabel(dept)"
                :value="dept.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="存放位置">
            <el-input v-model="surplusForm.location" maxlength="120" placeholder="选填" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="序列号">
            <el-input v-model="surplusForm.serial_no" maxlength="120" placeholder="选填" />
          </el-form-item>
          <el-form-item label="购入日期">
            <el-date-picker
              v-model="surplusForm.purchase_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选择日期"
              class="full-width"
            />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="购入金额">
            <el-input-number
              v-model="surplusForm.purchase_price"
              :min="0"
              :precision="2"
              controls-position="right"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="surplusForm.remark" maxlength="500" placeholder="选填" />
          </el-form-item>
        </div>
      </el-form>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="资产编号需全局唯一；提交盈亏处理并通过审批后会自动创建资产档案"
      />
      <template #footer>
        <el-button @click="surplusVisible = false">取消</el-button>
        <el-button type="primary" :loading="surplusSubmitting" @click="submitSurplus">
          确认登记
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="adjustmentVisible" title="提交盘盈盘亏处理" width="520px">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        :title="`本次将提交盘亏 ${detailTask?.missing_count || 0} 项、盘盈 ${detailTask?.surplus_count || 0} 项`"
        description="审批通过后，盘亏资产将标记为已报废并释放责任人；盘盈资产将按登记信息自动建档。"
      />
      <el-form label-position="top" class="dialog-form">
        <el-form-item label="差异说明">
          <el-input
            v-model="adjustmentReason"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="说明盘盈盘亏原因、核查过程等（选填）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustmentVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="adjustmentSubmitting"
          @click="submitAdjustment"
        >
          提交审批
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="approveVisible"
      :title="approveMode === 'approve' ? '通过盈亏处理' : '驳回盈亏处理'"
      width="520px"
    >
      <el-alert
        v-if="approveMode === 'approve'"
        type="warning"
        :closable="false"
        show-icon
        title="审批通过后将立即执行核销与建档，且不可撤销"
      />
      <el-form label-position="top" class="dialog-form">
        <el-form-item
          :label="approveMode === 'approve' ? '审批意见' : '驳回原因'"
          :required="approveMode === 'reject'"
        >
          <el-input
            v-model="approveComment"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            :placeholder="
              approveMode === 'approve' ? '审批意见（选填）' : '请说明驳回原因'
            "
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="approveVisible = false">取消</el-button>
        <el-button
          :type="approveMode === 'approve' ? 'success' : 'danger'"
          :loading="approveSubmitting"
          @click="submitApprove"
        >
          {{ approveMode === 'approve' ? '确认通过' : '确认驳回' }}
        </el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="reportVisible" size="70%" :with-header="false">
      <div v-loading="reportLoading" class="inventory-detail">
        <template v-if="reportData">
          <header class="detail-head">
            <div>
              <p class="page-eyebrow">INVENTORY REPORT</p>
              <h2 class="detail-title">{{ reportData.task.name }}</h2>
              <p class="detail-subtitle">
                <span class="mono">{{ reportData.task.task_no }}</span>
                · {{ reportData.task.scope_dept_name || '全部部门' }}
                · {{ reportData.task.scope_category_name || '全部分类' }}
                · 生成时间 {{ formatDateTime(reportData.generated_at) }}
              </p>
            </div>
            <div class="detail-head-actions">
              <el-button
                type="primary"
                :icon="Download"
                :loading="exporting"
                @click="exportReport"
              >
                导出 Excel
              </el-button>
              <el-button @click="reportVisible = false">关闭</el-button>
            </div>
          </header>

          <section class="detail-stats report-stats">
            <div class="stat-card">
              <span>资产总数</span>
              <strong>{{ reportData.task.total_assets }}</strong>
            </div>
            <div class="stat-card tone-success">
              <span>正常</span>
              <strong>{{ reportData.task.normal_count }}</strong>
            </div>
            <div class="stat-card tone-warning">
              <span>异常</span>
              <strong>{{ reportData.task.abnormal_count }}</strong>
            </div>
            <div class="stat-card tone-danger">
              <span>盘亏</span>
              <strong>{{ reportData.task.missing_count }}</strong>
            </div>
            <div class="stat-card tone-brand">
              <span>盘盈</span>
              <strong>{{ reportData.task.surplus_count }}</strong>
            </div>
            <div class="stat-card">
              <span>待核对</span>
              <strong>{{ reportData.task.pending_count }}</strong>
            </div>
          </section>

          <el-alert
            v-if="reportData.adjustment"
            :type="
              reportData.adjustment.status === 'APPROVED'
                ? 'success'
                : reportData.adjustment.status === 'REJECTED'
                  ? 'error'
                  : 'warning'
            "
            :closable="false"
            show-icon
            :title="`盈亏处理单 ${reportData.adjustment.adjustment_no}：${reportData.adjustment.status_label}`"
            :description="reportData.adjustment.review_comment || reportData.adjustment.reason || undefined"
            class="report-alert"
          />

          <section class="surface-card detail-panel report-section">
            <div class="section-head">
              <div>
                <strong>盘亏明细</strong>
                <small>盘点标记为盘亏的资产</small>
              </div>
              <el-tag type="danger" effect="light">
                {{ reportData.missing_items.length }} 项
              </el-tag>
            </div>
            <el-table :data="reportData.missing_items" size="small" empty-text="无盘亏资产">
              <el-table-column prop="asset_no" label="资产编号" width="150" />
              <el-table-column prop="asset_name" label="资产名称" min-width="150" />
              <el-table-column prop="category_name" label="分类" min-width="120" />
              <el-table-column prop="dept_name" label="部门" min-width="120" />
              <el-table-column prop="custodian_name" label="责任人" width="110" />
              <el-table-column prop="remark" label="说明" min-width="160" />
            </el-table>
          </section>

          <section class="surface-card detail-panel report-section">
            <div class="section-head">
              <div>
                <strong>异常明细</strong>
                <small>位置或状态与账面不一致的资产</small>
              </div>
              <el-tag type="warning" effect="light">
                {{ reportData.abnormal_items.length }} 项
              </el-tag>
            </div>
            <el-table :data="reportData.abnormal_items" size="small" empty-text="无异常资产">
              <el-table-column prop="asset_no" label="资产编号" width="150" />
              <el-table-column prop="asset_name" label="资产名称" min-width="150" />
              <el-table-column prop="dept_name" label="部门" min-width="120" />
              <el-table-column prop="location" label="账面位置" min-width="130" />
              <el-table-column prop="actual_location" label="实际位置" min-width="130" />
              <el-table-column prop="remark" label="说明" min-width="160" />
            </el-table>
          </section>

          <section class="surface-card detail-panel report-section">
            <div class="section-head">
              <div>
                <strong>盘盈明细</strong>
                <small>现场发现但未入账的资产</small>
              </div>
              <el-tag type="primary" effect="light">
                {{ reportData.surplus_items.length }} 项
              </el-tag>
            </div>
            <el-table :data="reportData.surplus_items" size="small" empty-text="无盘盈资产">
              <el-table-column prop="asset_no" label="资产编号" width="150" />
              <el-table-column prop="name" label="资产名称" min-width="150" />
              <el-table-column prop="category_name" label="分类" min-width="120" />
              <el-table-column prop="dept_name" label="部门" min-width="120" />
              <el-table-column prop="serial_no" label="序列号" min-width="140" />
              <el-table-column label="建档状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.applied_at ? 'success' : 'warning'" size="small">
                    {{ row.applied_at ? '已建档' : '待处理' }}
                  </el-tag>
                </template>
              </el-table-column>
            </el-table>
          </section>
        </template>
        <el-empty v-else-if="!reportLoading" description="暂无盘点报告" />
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.page-actions {
  display: flex;
  gap: 10px;
}

.panel {
  padding: 20px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.filter-keyword {
  width: 300px;
}

.filter-select {
  width: 150px;
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

.task-name {
  font-weight: 650;
  color: var(--text-1);
}

.progress-text {
  display: block;
  margin-top: 4px;
  color: var(--text-3);
  font-size: 11.5px;
}

.table-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.full-width {
  width: 100%;
}

.form-grid {
  display: grid;
  grid-template-columns: 1.6fr 0.6fr;
  gap: 0 16px;
  align-items: center;
}

.inventory-detail {
  padding: 4px 6px 20px;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 18px;
}

.detail-title {
  margin: 2px 0 4px;
  font-size: 22px;
  color: var(--text-1);
}

.detail-subtitle {
  margin: 0;
  color: var(--text-3);
  font-size: 12.5px;
}

.detail-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.detail-stats {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.report-stats {
  grid-template-columns: repeat(6, minmax(0, 1fr));
}

.section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.section-head strong {
  display: block;
  color: var(--text-1);
}

.section-head small {
  display: block;
  margin-top: 2px;
  color: var(--text-3);
  font-size: 12px;
}

.surplus-panel,
.adjustment-panel,
.report-section {
  margin-top: 16px;
}

.adjustment-panel .el-alert {
  margin-top: 4px;
}

.report-alert {
  margin-bottom: 4px;
}

.dialog-form {
  margin-top: 14px;
}

.tone-brand strong {
  color: var(--brand);
}

.stat-card {
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--surface-muted);
}

.stat-card span {
  color: var(--text-3);
  font-size: 12px;
}

.stat-card strong {
  display: block;
  margin-top: 4px;
  font-family: var(--font-number);
  font-size: 22px;
  color: var(--text-1);
}

.stat-card.tone-success strong {
  color: var(--success, #16a34a);
}

.stat-card.tone-warning strong {
  color: var(--warning, #d97706);
}

.stat-card.tone-danger strong {
  color: var(--danger, #dc2626);
}

.detail-progress {
  margin-bottom: 18px;
}

.scan-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;
  padding: 16px 18px;
  margin-bottom: 18px;
  border-radius: 14px;
  border: 1px dashed var(--brand);
  background: var(--brand-soft);
}

.scan-copy strong {
  display: block;
  color: var(--text-1);
}

.scan-copy span {
  display: block;
  margin-top: 2px;
  color: var(--text-3);
  font-size: 12px;
}

.scan-input {
  display: flex;
  gap: 10px;
  min-width: 380px;
}

.detail-panel {
  padding: 18px;
}

.action-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 12px;
  background: var(--surface-muted);
  border: 1px solid var(--border);
  margin-bottom: 16px;
}

.action-summary span {
  display: block;
  font-weight: 650;
  color: var(--text-1);
}

.action-summary small {
  display: block;
  margin-top: 2px;
  color: var(--text-3);
  font-size: 12px;
}

@media (max-width: 1180px) {
  .filter-keyword {
    width: 100%;
  }

  .detail-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .scan-input {
    min-width: 0;
    width: 100%;
  }
}
</style>
