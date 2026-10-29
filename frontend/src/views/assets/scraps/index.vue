<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'

import { assetOpsApi } from '@/api/assetOps'
import { useAuthStore } from '@/stores/auth'
import type { OpsAsset, ScrapItem, ScrapStatus } from '@/types/assetOps'
import {
  SCRAP_STATUS_LABELS,
  isScrapInterrupted,
  scrapActive,
  scrapSteps,
} from '@/types/assetOps'
import { formatDateTime } from '@/utils/format'

type ActionMode = 'approve' | 'reject' | 'confirm'

const auth = useAuthStore()
const route = useRoute()
const focusId = (() => {
  const raw = route.query.focus
  const value = typeof raw === 'string' ? Number(raw) : Number.NaN
  return Number.isInteger(value) && value > 0 ? value : null
})()

const loading = ref(false)
const scraps = ref<ScrapItem[]>([])
const total = ref(0)
const query = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  status: undefined as ScrapStatus | undefined,
})
const statusOptions = Object.entries(SCRAP_STATUS_LABELS) as Array<
  [ScrapStatus, string]
>

const createVisible = ref(false)
const createSubmitting = ref(false)
const assetOptions = ref<OpsAsset[]>([])
const assetSearching = ref(false)
const selectedAsset = ref<OpsAsset | null>(null)
const form = reactive({
  asset_id: undefined as number | undefined,
  reason: '',
  disposal_method: '',
  residual_value: undefined as number | undefined,
})

const detailVisible = ref(false)
const detailItem = ref<ScrapItem | null>(null)

const actionVisible = ref(false)
const actionMode = ref<ActionMode>('approve')
const actionItem = ref<ScrapItem | null>(null)
const actionComment = ref('')
const actionSubmitting = ref(false)

const actionTitle = computed(() => {
  const titles: Record<ActionMode, string> = {
    approve: '审批报废',
    reject: '驳回报废',
    confirm: '确认报废',
  }
  return titles[actionMode.value]
})

const canCreate = computed(() => auth.hasPerm('asset:scrap:create'))

async function fetchScraps(): Promise<void> {
  loading.value = true
  try {
    const page = await assetOpsApi.listScraps({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      status: query.status,
    })
    scraps.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  query.page = 1
  void fetchScraps()
}

function resetFilters(): void {
  query.keyword = ''
  query.status = undefined
  query.page = 1
  void fetchScraps()
}

async function searchAssets(keyword: string): Promise<void> {
  assetSearching.value = true
  try {
    const page = await assetOpsApi.operableAssets({
      purpose: 'scrap',
      page: 1,
      page_size: 30,
      keyword: keyword || undefined,
    })
    const pinned = selectedAsset.value ? [selectedAsset.value] : []
    assetOptions.value = [
      ...pinned,
      ...page.items.filter((item) => item.id !== selectedAsset.value?.id),
    ]
  } finally {
    assetSearching.value = false
  }
}

function handleAssetChange(id: number): void {
  selectedAsset.value = assetOptions.value.find((item) => item.id === id) ?? null
}

async function openCreate(): Promise<void> {
  form.asset_id = undefined
  form.reason = ''
  form.disposal_method = ''
  form.residual_value = undefined
  selectedAsset.value = null
  assetOptions.value = []
  createVisible.value = true
  await searchAssets('')
}

async function submitCreate(): Promise<void> {
  if (!form.asset_id) {
    ElMessage.warning('请选择要报废的资产')
    return
  }
  if (form.reason.trim().length < 2) {
    ElMessage.warning('请填写报废原因（至少 2 个字）')
    return
  }
  createSubmitting.value = true
  try {
    await assetOpsApi.createScrap({
      asset_id: form.asset_id,
      reason: form.reason.trim(),
      disposal_method: form.disposal_method.trim() || null,
      residual_value: form.residual_value ?? null,
    })
    ElMessage.success('报废申请已提交，等待审批')
    createVisible.value = false
    handleSearch()
  } finally {
    createSubmitting.value = false
  }
}

function openDetail(row: ScrapItem): void {
  detailItem.value = row
  detailVisible.value = true
}

async function openFocused(): Promise<void> {
  if (!focusId) return
  const row = scraps.value.find((item) => item.id === focusId)
  if (row) {
    openDetail(row)
    return
  }
  try {
    detailItem.value = await assetOpsApi.getScrap(focusId)
    detailVisible.value = true
  } catch {
    // 目标单据无权限或已失效时停留在列表页
  }
}

function openAction(row: ScrapItem, mode: ActionMode): void {
  actionItem.value = row
  actionMode.value = mode
  actionComment.value = ''
  actionVisible.value = true
}

async function submitAction(): Promise<void> {
  const item = actionItem.value
  if (!item) return
  if (actionMode.value === 'reject' && !actionComment.value.trim()) {
    ElMessage.warning('请填写驳回原因')
    return
  }
  actionSubmitting.value = true
  try {
    if (actionMode.value === 'approve') {
      await assetOpsApi.approveScrap(item.id, {
        version: item.asset_version,
        comment: actionComment.value || null,
      })
      ElMessage.success('审批通过，资产已转入待报废')
    } else if (actionMode.value === 'reject') {
      await assetOpsApi.rejectScrap(item.id, actionComment.value)
      ElMessage.success('报废单已驳回')
    } else {
      await assetOpsApi.confirmScrap(item.id, {
        version: item.asset_version,
        comment: actionComment.value || null,
      })
      ElMessage.success('报废完成，资产已标记为已报废')
    }
    actionVisible.value = false
    detailVisible.value = false
    detailItem.value = null
    await fetchScraps()
  } finally {
    actionSubmitting.value = false
  }
}

async function cancelScrap(row: ScrapItem): Promise<void> {
  await ElMessageBox.confirm(
    `确定撤销报废单 ${row.scrap_no} 吗？资产状态不会发生变化。`,
    '撤销报废',
    { type: 'warning', confirmButtonText: '撤销', cancelButtonText: '返回' },
  )
  await assetOpsApi.cancelScrap(row.id)
  ElMessage.success('报废单已撤销')
  await fetchScraps()
}

onMounted(async () => {
  await fetchScraps()
  await openFocused()
})
</script>

<template>
  <div class="page scrap-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">ASSET DISPOSAL</p>
        <h1 class="page-title">资产报废</h1>
        <p class="page-subtitle">
          报废审批通过后资产转为「待报废」，确认处置后正式报废并清空责任人。全流程写入状态历史与审计日志。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" :loading="loading" @click="fetchScraps">刷新</el-button>
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">
          发起报废
        </el-button>
      </div>
    </header>

    <section class="surface-card panel">
      <div class="filter-bar">
        <el-input
          v-model="query.keyword"
          :prefix-icon="Search"
          placeholder="报废单号 / 资产编号 / 资产名称 / 申请人"
          clearable
          class="filter-keyword"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select
          v-model="query.status"
          placeholder="单据状态"
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

      <el-table v-loading="loading" :data="scraps" row-key="id" empty-text="当前没有报废单">
        <el-table-column label="报废单" min-width="190">
          <template #default="{ row }">
            <div class="stack-cell">
              <span class="mono">{{ row.scrap_no }}</span>
              <small>{{ formatDateTime(row.created_at) }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="资产" min-width="210">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.asset_name }}</span>
              <small>{{ row.asset_no }} · {{ row.asset_status_label }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="报废原因" min-width="220">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.reason }}</span>
              <small>
                处置方式：{{ row.disposal_method || '待确定' }} · 残值
                {{ row.residual_value != null ? `¥${row.residual_value}` : '未登记' }}
              </small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="申请人" min-width="140">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.applicant_name }}</span>
              <small>{{ row.applicant_dept_name || '未分配部门' }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="130">
          <template #default="{ row }">
            <el-tag :type="row.status_tag_type" effect="light">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="250" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button
              v-if="row.can_approve"
              link
              type="success"
              @click="openAction(row, 'approve')"
            >
              审批
            </el-button>
            <el-button
              v-if="row.can_reject"
              link
              type="danger"
              @click="openAction(row, 'reject')"
            >
              驳回
            </el-button>
            <el-button
              v-if="row.can_confirm"
              link
              type="danger"
              @click="openAction(row, 'confirm')"
            >
              确认报废
            </el-button>
            <el-button v-if="row.can_cancel" link type="warning" @click="cancelScrap(row)">
              撤销
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
          @current-change="fetchScraps"
          @size-change="handleSearch"
        />
      </div>
    </section>

    <el-dialog v-model="createVisible" title="发起资产报废" width="600px">
      <el-form label-position="top">
        <el-form-item label="报废资产" required>
          <el-select
            v-model="form.asset_id"
            filterable
            remote
            clearable
            reserve-keyword
            :remote-method="searchAssets"
            :loading="assetSearching"
            placeholder="输入资产编号或名称搜索"
            class="full-width"
            @change="handleAssetChange"
          >
            <el-option
              v-for="asset in assetOptions"
              :key="asset.id"
              :label="`${asset.asset_no} · ${asset.name}`"
              :value="asset.id"
            >
              <div class="option-cell">
                <span>{{ asset.asset_no }} · {{ asset.name }}</span>
                <small>
                  {{ asset.status_label }} · {{ asset.dept_name || '未分配部门' }} ·
                  {{ asset.custodian_name || '无责任人' }}
                </small>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <div v-if="selectedAsset" class="asset-preview">
          <div>
            <span>{{ selectedAsset.name }}</span>
            <small>
              {{ selectedAsset.asset_no }} · {{ selectedAsset.category_name || '未分类' }} ·
              {{ selectedAsset.location || '未登记位置' }}
            </small>
          </div>
          <el-tag type="primary" effect="light">{{ selectedAsset.status_label }}</el-tag>
        </div>

        <el-form-item label="报废原因" required>
          <el-input
            v-model="form.reason"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="请说明资产损坏情况或报废依据"
          />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="处置方式">
            <el-input
              v-model="form.disposal_method"
              maxlength="120"
              placeholder="如：环保回收 / 资产处置商回收 / 封存"
            />
          </el-form-item>
          <el-form-item label="残值金额">
            <el-input-number
              v-model="form.residual_value"
              :min="0"
              :precision="2"
              controls-position="right"
              class="full-width"
              placeholder="选填"
            />
          </el-form-item>
        </div>
      </el-form>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="存在进行中的领用、借用或调拨单据的资产不可发起报废"
      />
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSubmitting" @click="submitCreate">
          提交报废申请
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="报废单详情" width="680px">
      <template v-if="detailItem">
        <el-steps
          :active="scrapActive(detailItem.status)"
          :process-status="isScrapInterrupted(detailItem.status) ? 'error' : 'process'"
          finish-status="success"
          align-center
          class="flow-steps"
        >
          <el-step v-for="step in scrapSteps()" :key="step" :title="step" />
        </el-steps>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="报废单号">{{ detailItem.scrap_no }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="detailItem.status_tag_type" effect="light">
              {{ detailItem.status_label }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="资产">
            {{ detailItem.asset_name }}（{{ detailItem.asset_no }}）
          </el-descriptions-item>
          <el-descriptions-item label="当前资产状态">
            {{ detailItem.asset_status_label }}
          </el-descriptions-item>
          <el-descriptions-item label="原状态">
            {{ detailItem.from_status_label }}
          </el-descriptions-item>
          <el-descriptions-item label="原责任人">
            {{ detailItem.from_custodian_name || '无责任人' }}
          </el-descriptions-item>
          <el-descriptions-item label="原部门">
            {{ detailItem.from_dept_name || '未分配部门' }}
          </el-descriptions-item>
          <el-descriptions-item label="原位置">
            {{ detailItem.from_location || '未登记位置' }}
          </el-descriptions-item>
          <el-descriptions-item label="申请人">
            {{ detailItem.applicant_name }}（{{ detailItem.applicant_dept_name || '未分配部门' }}）
          </el-descriptions-item>
          <el-descriptions-item label="申请时间">
            {{ formatDateTime(detailItem.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="审批人">
            {{ detailItem.approver_name || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="审批时间">
            {{ formatDateTime(detailItem.approved_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="确认人">
            {{ detailItem.completed_by_name || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="确认时间">
            {{ formatDateTime(detailItem.completed_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="报废原因" :span="2">
            {{ detailItem.reason }}
          </el-descriptions-item>
          <el-descriptions-item label="处置方式" :span="2">
            {{ detailItem.disposal_method || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="残值金额" :span="2">
            {{ detailItem.residual_value != null ? `¥${detailItem.residual_value}` : '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="审批意见" :span="2">
            {{ detailItem.approval_comment || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="确认备注" :span="2">
            {{ detailItem.completion_comment || '—' }}
          </el-descriptions-item>
        </el-descriptions>
      </template>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button
          v-if="detailItem?.can_approve"
          type="success"
          @click="detailItem && openAction(detailItem, 'approve')"
        >
          审批
        </el-button>
        <el-button
          v-if="detailItem?.can_confirm"
          type="danger"
          @click="detailItem && openAction(detailItem, 'confirm')"
        >
          确认报废
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="actionVisible" :title="actionTitle" width="520px">
      <div v-if="actionItem" class="action-summary">
        <div>
          <span>{{ actionItem.asset_name }}</span>
          <small>{{ actionItem.asset_no }} · {{ actionItem.scrap_no }}</small>
        </div>
        <el-tag :type="actionItem.status_tag_type" effect="light">
          {{ actionItem.status_label }}
        </el-tag>
      </div>

      <el-form label-position="top">
        <el-form-item
          :label="
            actionMode === 'approve'
              ? '审批意见（选填）'
              : actionMode === 'reject'
                ? '驳回原因（必填）'
                : '确认备注（选填）'
          "
        >
          <el-input
            v-model="actionComment"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            :placeholder="actionMode === 'reject' ? '请说明驳回原因' : '可填写补充说明'"
          />
        </el-form-item>
      </el-form>

      <el-alert
        v-if="actionMode === 'approve'"
        type="warning"
        :closable="false"
        show-icon
        title="审批通过后资产状态将变为「待报废」，并写入状态历史与审计日志"
      />
      <el-alert
        v-if="actionMode === 'confirm'"
        type="error"
        :closable="false"
        show-icon
        title="确认报废后资产状态将变为「已报废」并清空责任人，该操作不可回退"
      />
      <template #footer>
        <el-button @click="actionVisible = false">取消</el-button>
        <el-button
          :type="actionMode === 'approve' ? 'primary' : 'danger'"
          :loading="actionSubmitting"
          @click="submitAction"
        >
          确认{{ actionTitle }}
        </el-button>
      </template>
    </el-dialog>
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
  width: 320px;
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

.table-footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.full-width {
  width: 100%;
}

.option-cell {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.option-cell small {
  color: var(--text-3);
  font-size: 11px;
}

.asset-preview {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: var(--surface-muted);
}

.asset-preview span {
  font-weight: 650;
  color: var(--text-1);
}

.asset-preview small {
  display: block;
  margin-top: 2px;
  color: var(--text-3);
  font-size: 12px;
}

.flow-steps {
  margin-bottom: 22px;
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

.form-grid {
  display: grid;
  grid-template-columns: 1.4fr 0.8fr;
  gap: 0 16px;
  align-items: center;
}

@media (max-width: 1180px) {
  .filter-keyword {
    width: 100%;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
