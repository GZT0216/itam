<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Search } from '@element-plus/icons-vue'

import { maintenanceApi } from '@/api/maintenance'
import { useAuthStore } from '@/stores/auth'
import type {
  Maintenance,
  MaintenanceAsset,
  MaintenancePriority,
  MaintenanceRecordType,
  MaintenanceStatus,
  RepairerOption,
} from '@/types/maintenance'
import {
  MAINTENANCE_PRIORITY_LABELS,
  MAINTENANCE_RECORD_TYPE_LABELS,
  MAINTENANCE_STATUS_LABELS,
  isMaintenanceInterrupted,
  maintenanceActive,
  maintenanceSteps,
} from '@/types/maintenance'
import { formatDateTime } from '@/utils/format'

const auth = useAuthStore()
const route = useRoute()
const focusId = (() => {
  const raw = route.query.focus
  const value = typeof raw === 'string' ? Number(raw) : Number.NaN
  return Number.isInteger(value) && value > 0 ? value : null
})()
const canCreate = computed(() => auth.hasPerm('asset:maintenance:create'))

const loading = ref(false)
const rows = ref<Maintenance[]>([])
const total = ref(0)
const query = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  status: undefined as MaintenanceStatus | undefined,
  priority: undefined as MaintenancePriority | undefined,
})
const statusOptions = Object.entries(MAINTENANCE_STATUS_LABELS) as Array<
  [MaintenanceStatus, string]
>
const priorityOptions = Object.entries(MAINTENANCE_PRIORITY_LABELS) as Array<
  [MaintenancePriority, string]
>
const recordTypeOptions = Object.entries(MAINTENANCE_RECORD_TYPE_LABELS) as Array<
  [MaintenanceRecordType, string]
>

const createVisible = ref(false)
const createSubmitting = ref(false)
const assetOptions = ref<MaintenanceAsset[]>([])
const assetLoading = ref(false)
const createForm = reactive({
  asset_id: undefined as number | undefined,
  priority: 'NORMAL' as MaintenancePriority,
  expected_date: '',
  fault_description: '',
})

const detailVisible = ref(false)
const detail = ref<Maintenance | null>(null)
const detailLoading = ref(false)

const approveVisible = ref(false)
const approveSubmitting = ref(false)
const approveTarget = ref<Maintenance | null>(null)
const repairers = ref<RepairerOption[]>([])
const repairerLoading = ref(false)
const approveForm = reactive({
  repairer_id: undefined as number | undefined,
  expected_date: '',
  comment: '',
})

const recordVisible = ref(false)
const recordSubmitting = ref(false)
const recordForm = reactive({
  record_type: 'PROGRESS' as MaintenanceRecordType,
  content: '',
  cost: undefined as number | undefined,
  occurred_at: '',
})

const completeVisible = ref(false)
const completeSubmitting = ref(false)
const completeForm = reactive({ repair_result: '' })

const acceptVisible = ref(false)
const acceptSubmitting = ref(false)
const acceptComment = ref('')

function money(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return `¥${Number(value).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

async function fetchRows(): Promise<void> {
  loading.value = true
  try {
    const page = await maintenanceApi.list({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword || undefined,
      status: query.status,
      priority: query.priority,
    })
    rows.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
}

function handleSearch(): void {
  query.page = 1
  void fetchRows()
}

function resetFilters(): void {
  query.keyword = ''
  query.status = undefined
  query.priority = undefined
  query.page = 1
  void fetchRows()
}

async function reloadAll(): Promise<void> {
  await fetchRows()
  if (detailVisible.value && detail.value) {
    try {
      detail.value = await maintenanceApi.get(detail.value.id)
    } catch {
      detailVisible.value = false
    }
  }
}

async function loadAssetOptions(keyword?: string): Promise<void> {
  assetLoading.value = true
  try {
    const page = await maintenanceApi.optionsAssets({
      page: 1,
      page_size: 50,
      keyword: keyword || undefined,
    })
    assetOptions.value = page.items
  } finally {
    assetLoading.value = false
  }
}

async function openCreate(): Promise<void> {
  createForm.asset_id = undefined
  createForm.priority = 'NORMAL'
  createForm.expected_date = ''
  createForm.fault_description = ''
  assetOptions.value = []
  createVisible.value = true
  await loadAssetOptions()
}

async function submitCreate(): Promise<void> {
  if (!createForm.asset_id) {
    ElMessage.warning('请选择需要报修的资产')
    return
  }
  const description = createForm.fault_description.trim()
  if (description.length < 2) {
    ElMessage.warning('请填写故障描述，至少 2 个字符')
    return
  }
  createSubmitting.value = true
  try {
    await maintenanceApi.create({
      asset_id: createForm.asset_id,
      fault_description: description,
      priority: createForm.priority,
      expected_date: createForm.expected_date || null,
    })
    ElMessage.success('报修申请已提交，等待审批')
    createVisible.value = false
    handleSearch()
  } finally {
    createSubmitting.value = false
  }
}

async function openDetail(row: Maintenance): Promise<void> {
  detail.value = row
  detailVisible.value = true
  detailLoading.value = true
  try {
    detail.value = await maintenanceApi.get(row.id)
  } catch {
    detailVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

async function openFocused(): Promise<void> {
  if (!focusId) return
  const row = rows.value.find((item) => item.id === focusId)
  if (row) {
    await openDetail(row)
    return
  }
  try {
    detail.value = await maintenanceApi.get(focusId)
    detailVisible.value = true
  } catch {
    // 目标工单无权限或已失效时停留在列表页
  }
}

async function loadRepairers(keyword?: string): Promise<void> {
  repairerLoading.value = true
  try {
    repairers.value = await maintenanceApi.optionsRepairers(keyword)
  } finally {
    repairerLoading.value = false
  }
}

async function openApprove(item: Maintenance): Promise<void> {
  approveTarget.value = item
  approveForm.repairer_id = item.repairer_id ?? undefined
  approveForm.expected_date = item.expected_date ?? ''
  approveForm.comment = ''
  approveVisible.value = true
  await loadRepairers()
}

async function submitApprove(): Promise<void> {
  const target = approveTarget.value
  if (!target) return
  if (!approveForm.repairer_id) {
    ElMessage.warning('请选择维修人员')
    return
  }
  approveSubmitting.value = true
  try {
    const updated = await maintenanceApi.approve(target.id, {
      version: target.asset_version,
      repairer_id: approveForm.repairer_id,
      expected_date: approveForm.expected_date || null,
      comment: approveForm.comment.trim() || null,
    })
    if (detailVisible.value && detail.value?.id === updated.id) {
      detail.value = updated
    }
    approveVisible.value = false
    ElMessage.success('审批通过，资产已转入维修中')
    await fetchRows()
  } catch {
    approveVisible.value = false
    await reloadAll()
  } finally {
    approveSubmitting.value = false
  }
}

async function rejectOrder(): Promise<void> {
  const target = detail.value
  if (!target) return
  let comment = ''
  try {
    const result = await ElMessageBox.prompt('请填写驳回原因', '驳回维修申请', {
      confirmButtonText: '确认驳回',
      cancelButtonText: '返回',
      inputType: 'textarea',
      inputPlaceholder: '驳回原因（选填）',
      inputValidator: () => true,
    })
    comment = (result.value || '').trim()
  } catch {
    return
  }
  try {
    await maintenanceApi.reject(target.id, comment || null)
    ElMessage.success('维修申请已驳回')
    await reloadAll()
  } catch {
    await reloadAll()
  }
}

async function startRepair(item: Maintenance): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确认开始维修工单 ${item.maintenance_no} 吗？开始后可登记维修与费用记录。`,
      '开始维修',
      { confirmButtonText: '开始维修', cancelButtonText: '返回', type: 'warning' },
    )
  } catch {
    return
  }
  try {
    const updated = await maintenanceApi.start(item.id)
    if (detailVisible.value && detail.value?.id === updated.id) {
      detail.value = updated
    }
    ElMessage.success('已开始维修')
    await fetchRows()
  } catch {
    await reloadAll()
  }
}

function openRecord(): void {
  recordForm.record_type = 'PROGRESS'
  recordForm.content = ''
  recordForm.cost = undefined
  recordForm.occurred_at = ''
  recordVisible.value = true
}

async function submitRecord(): Promise<void> {
  const target = detail.value
  if (!target) return
  const content = recordForm.content.trim()
  if (content.length < 2) {
    ElMessage.warning('请填写记录内容，至少 2 个字符')
    return
  }
  if (recordForm.record_type === 'EXPENSE' && (recordForm.cost === undefined || recordForm.cost === null)) {
    ElMessage.warning('费用记录必须填写金额')
    return
  }
  recordSubmitting.value = true
  try {
    const updated = await maintenanceApi.addRecord(target.id, {
      record_type: recordForm.record_type,
      content,
      cost: recordForm.record_type === 'EXPENSE' ? recordForm.cost : null,
      occurred_at: recordForm.occurred_at || null,
    })
    detail.value = updated
    recordVisible.value = false
    ElMessage.success('维修记录已保存')
    await fetchRows()
  } catch {
    await reloadAll()
  } finally {
    recordSubmitting.value = false
  }
}

function openComplete(): void {
  completeForm.repair_result = ''
  completeVisible.value = true
}

async function submitComplete(): Promise<void> {
  const target = detail.value
  if (!target) return
  const result = completeForm.repair_result.trim()
  if (result.length < 2) {
    ElMessage.warning('请填写维修结果，至少 2 个字符')
    return
  }
  completeSubmitting.value = true
  try {
    const updated = await maintenanceApi.complete(target.id, {
      repair_result: result,
    })
    detail.value = updated
    completeVisible.value = false
    ElMessage.success('维修已完成，等待验收')
    await fetchRows()
  } catch {
    await reloadAll()
  } finally {
    completeSubmitting.value = false
  }
}

function openAccept(): void {
  acceptComment.value = ''
  acceptVisible.value = true
}

async function submitAccept(): Promise<void> {
  const target = detail.value
  if (!target) return
  acceptSubmitting.value = true
  try {
    const updated = await maintenanceApi.accept(target.id, {
      version: target.asset_version,
      comment: acceptComment.value.trim() || null,
    })
    detail.value = updated
    acceptVisible.value = false
    ElMessage.success('验收完成，资产已恢复原状态')
    await fetchRows()
  } catch {
    acceptVisible.value = false
    await reloadAll()
  } finally {
    acceptSubmitting.value = false
  }
}

async function cancelOrder(item: Maintenance): Promise<void> {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt(
      `确定取消维修工单 ${item.maintenance_no} 吗？如资产已进入维修中，取消后将恢复原状态。`,
      '取消维修工单',
      {
        confirmButtonText: '取消工单',
        cancelButtonText: '返回',
        inputType: 'textarea',
        inputPlaceholder: '取消原因（选填）',
        inputValidator: () => true,
      },
    )
    reason = (result.value || '').trim()
  } catch {
    return
  }
  try {
    const updated = await maintenanceApi.cancel(item.id, reason || null)
    if (detailVisible.value && detail.value?.id === updated.id) {
      detail.value = updated
    }
    ElMessage.success('维修工单已取消')
    await fetchRows()
  } catch {
    await reloadAll()
  }
}

onMounted(async () => {
  await fetchRows()
  await openFocused()
})
</script>

<template>
  <div class="page maintenance-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">REPAIR &amp; MAINTENANCE</p>
        <h1 class="page-title">维修管理</h1>
        <p class="page-subtitle">
          报修申请经审批指派后，资产自动进入维修中；维修人员登记过程与费用，验收通过后资产恢复原状态，全过程写入历史快照与审计日志。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" :loading="loading" @click="fetchRows">刷新</el-button>
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">
          提交报修
        </el-button>
      </div>
    </header>

    <section class="surface-card panel">
      <div class="filter-bar">
        <el-input
          v-model="query.keyword"
          :prefix-icon="Search"
          placeholder="工单号 / 资产 / 申请人 / 维修人"
          clearable
          class="filter-keyword"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select
          v-model="query.status"
          placeholder="工单状态"
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
        <el-select
          v-model="query.priority"
          placeholder="优先级"
          clearable
          class="filter-select"
          @change="handleSearch"
        >
          <el-option
            v-for="[value, label] in priorityOptions"
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

      <el-table
        v-loading="loading"
        :data="rows"
        row-key="id"
        empty-text="当前没有维修工单"
      >
        <el-table-column label="维修工单" min-width="180">
          <template #default="{ row }">
            <div class="stack-cell">
              <span class="mono">{{ row.maintenance_no }}</span>
              <small>{{ formatDateTime(row.created_at) }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="资产" min-width="190">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.asset_name }}</span>
              <small class="mono">{{ row.asset_no }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="故障 / 优先级" min-width="240">
          <template #default="{ row }">
            <div class="stack-cell">
              <span class="fault-text">{{ row.fault_description }}</span>
              <small>
                <el-tag :type="row.priority_tag_type" size="small" effect="plain">
                  {{ row.priority_label }}
                </el-tag>
              </small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="报送部门 / 报修人" min-width="170">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.from_dept_name || '未归属部门' }}</span>
              <small>{{ row.applicant_name }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="维修人" min-width="120">
          <template #default="{ row }">
            <span :class="{ muted: !row.repairer_name }">
              {{ row.repairer_name || '待指派' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="累计费用" width="120">
          <template #default="{ row }">{{ money(row.total_cost) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="row.status_tag_type" effect="light">{{ row.status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row)">详情</el-button>
            <el-button v-if="row.can_approve" link type="primary" @click="openApprove(row)">
              审批
            </el-button>
            <el-button v-if="row.can_start" link type="success" @click="startRepair(row)">
              开始维修
            </el-button>
            <el-button v-if="row.can_accept" link type="success" @click="openDetail(row)">
              验收
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
          @current-change="fetchRows"
          @size-change="handleSearch"
        />
      </div>
    </section>

    <el-dialog v-model="createVisible" title="提交报修申请" width="640px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="报修资产" required>
          <el-select
            v-model="createForm.asset_id"
            filterable
            remote
            clearable
            :remote-method="loadAssetOptions"
            :loading="assetLoading"
            placeholder="输入资产编号或名称搜索"
            class="full-width"
          >
            <el-option
              v-for="asset in assetOptions"
              :key="asset.id"
              :label="`${asset.asset_no} · ${asset.name}`"
              :value="asset.id"
            >
              <div class="asset-option">
                <span>{{ asset.asset_no }} · {{ asset.name }}</span>
                <small>
                  {{ asset.dept_name || '未归属部门' }} ·
                  {{ asset.custodian_name || '无责任人' }} ·
                  {{ asset.location || '未指定位置' }}
                </small>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="优先级">
            <el-select v-model="createForm.priority" class="full-width">
              <el-option
                v-for="[value, label] in priorityOptions"
                :key="value"
                :label="label"
                :value="value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="期望完成日期">
            <el-date-picker
              v-model="createForm.expected_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选填"
              class="full-width"
            />
          </el-form-item>
        </div>
        <el-form-item label="故障描述" required>
          <el-input
            v-model="createForm.fault_description"
            type="textarea"
            :rows="4"
            maxlength="1000"
            show-word-limit
            placeholder="请描述故障现象、出现时间及影响范围"
          />
        </el-form-item>
      </el-form>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="提交后进入待审批状态；审批通过并指派维修人员后，资产状态将自动变更为维修中"
      />
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSubmitting" @click="submitCreate">
          提交报修
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailVisible" title="维修工单详情" width="860px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <el-steps
            :active="maintenanceActive(detail.status)"
            :process-status="isMaintenanceInterrupted(detail.status) ? 'error' : 'process'"
            finish-status="success"
            align-center
            class="flow-steps"
          >
            <el-step v-for="step in maintenanceSteps()" :key="step" :title="step" />
          </el-steps>

          <el-descriptions :column="2" border>
            <el-descriptions-item label="工单号">
              <span class="mono">{{ detail.maintenance_no }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="detail.status_tag_type" effect="light">
                {{ detail.status_label }}
              </el-tag>
              <el-tag :type="detail.priority_tag_type" effect="plain" class="inline-tag">
                {{ detail.priority_label }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="资产">
              {{ detail.asset_name }}（{{ detail.asset_no }}）
            </el-descriptions-item>
            <el-descriptions-item label="资产状态">
              {{ detail.asset_status_label }}
              <span class="muted">（维修前：{{ detail.from_status_label }}）</span>
            </el-descriptions-item>
            <el-descriptions-item label="报送部门">
              {{ detail.from_dept_name || '未归属部门' }}
            </el-descriptions-item>
            <el-descriptions-item label="报修人">
              {{ detail.applicant_name }}
            </el-descriptions-item>
            <el-descriptions-item label="资产责任人">
              {{ detail.from_custodian_name || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="存放位置">
              {{ detail.from_location || '未指定位置' }}
            </el-descriptions-item>
            <el-descriptions-item label="期望完成日期">
              {{ detail.expected_date || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="维修人">
              {{ detail.repairer_name || '待指派' }}
            </el-descriptions-item>
            <el-descriptions-item label="审批人">
              {{ detail.approver_name || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="审批时间">
              {{ formatDateTime(detail.approved_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="开始维修">
              {{ formatDateTime(detail.started_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="完成维修">
              {{ formatDateTime(detail.finished_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="累计费用">
              {{ money(detail.total_cost) }}
            </el-descriptions-item>
            <el-descriptions-item label="验收人">
              {{ detail.accepted_by_name || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="验收时间">
              {{ formatDateTime(detail.accepted_at) }}
            </el-descriptions-item>
            <el-descriptions-item v-if="detail.cancelled_at" label="取消时间">
              {{ formatDateTime(detail.cancelled_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="故障描述" :span="2">
              {{ detail.fault_description }}
            </el-descriptions-item>
            <el-descriptions-item v-if="detail.repair_result" label="维修结果" :span="2">
              {{ detail.repair_result }}
            </el-descriptions-item>
            <el-descriptions-item v-if="detail.approval_comment" label="审批意见" :span="2">
              {{ detail.approval_comment }}
            </el-descriptions-item>
            <el-descriptions-item
              v-if="detail.acceptance_comment"
              label="验收意见"
              :span="2"
            >
              {{ detail.acceptance_comment }}
            </el-descriptions-item>
            <el-descriptions-item v-if="detail.cancel_reason" label="取消原因" :span="2">
              {{ detail.cancel_reason }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="detail-subtitle">维修记录与费用</div>
          <el-timeline v-if="detail.records.length">
            <el-timeline-item
              v-for="record in detail.records"
              :key="record.id"
              :timestamp="formatDateTime(record.occurred_at)"
              placement="top"
              :type="record.record_type === 'EXPENSE' ? 'warning' : 'primary'"
            >
              <div class="record-card">
                <div class="record-head">
                  <el-tag
                    :type="record.record_type === 'EXPENSE' ? 'warning' : 'primary'"
                    size="small"
                    effect="plain"
                  >
                    {{ record.record_type_label }}
                  </el-tag>
                  <strong v-if="record.cost !== null">{{ money(record.cost) }}</strong>
                </div>
                <p>{{ record.content }}</p>
                <small>{{ record.operator_name || '—' }}</small>
              </div>
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无维修记录" :image-size="70" />
        </template>
      </div>

      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
        <el-button v-if="detail?.can_cancel" type="warning" plain @click="cancelOrder(detail)">
          取消工单
        </el-button>
        <el-button v-if="detail?.can_reject" type="danger" plain @click="rejectOrder">
          驳回
        </el-button>
        <el-button v-if="detail?.can_approve" type="primary" @click="openApprove(detail)">
          审批通过
        </el-button>
        <el-button v-if="detail?.can_start" type="primary" @click="startRepair(detail)">
          开始维修
        </el-button>
        <el-button v-if="detail?.can_add_record" @click="openRecord">登记记录</el-button>
        <el-button v-if="detail?.can_complete" type="primary" @click="openComplete">
          完成维修
        </el-button>
        <el-button v-if="detail?.can_accept" type="primary" @click="openAccept">
          验收通过
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="approveVisible" title="审批维修申请" width="580px">
      <div v-if="approveTarget" class="action-summary">
        <div>
          <span>{{ approveTarget.maintenance_no }} · {{ approveTarget.asset_name }}</span>
          <small>
            {{ approveTarget.asset_no }} · {{ approveTarget.from_dept_name || '未归属部门' }}
          </small>
        </div>
        <el-tag :type="approveTarget.status_tag_type" effect="light">
          {{ approveTarget.status_label }}
        </el-tag>
      </div>

      <el-form label-position="top">
        <el-form-item label="指派维修人员" required>
          <el-select
            v-model="approveForm.repairer_id"
            filterable
            remote
            :remote-method="loadRepairers"
            :loading="repairerLoading"
            placeholder="选择维修人员"
            class="full-width"
          >
            <el-option
              v-for="repairer in repairers"
              :key="repairer.id"
              :label="`${repairer.name} · ${repairer.dept_name || '未归属部门'}`"
              :value="repairer.id"
            />
          </el-select>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="期望完成日期">
            <el-date-picker
              v-model="approveForm.expected_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选填"
              class="full-width"
            />
          </el-form-item>
        </div>
        <el-form-item label="审批意见">
          <el-input
            v-model="approveForm.comment"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="选填"
          />
        </el-form-item>
      </el-form>

      <el-alert
        type="warning"
        :closable="false"
        show-icon
        title="审批通过后资产状态将自动变更为维修中，并写入状态历史与审计日志"
      />
      <template #footer>
        <el-button @click="approveVisible = false">取消</el-button>
        <el-button type="primary" :loading="approveSubmitting" @click="submitApprove">
          审批通过
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="recordVisible" title="登记维修记录" width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="记录类型">
          <el-radio-group v-model="recordForm.record_type">
            <el-radio-button
              v-for="[value, label] in recordTypeOptions"
              :key="value"
              :value="value"
            >
              {{ label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="记录内容" required>
          <el-input
            v-model="recordForm.content"
            type="textarea"
            :rows="3"
            maxlength="1000"
            show-word-limit
            :placeholder="
              recordForm.record_type === 'EXPENSE'
                ? '如：更换主板、外购配件等'
                : '如：拆机检查、更换配件、测试情况等'
            "
          />
        </el-form-item>
        <div v-if="recordForm.record_type === 'EXPENSE'" class="form-grid">
          <el-form-item label="费用金额（元）" required>
            <el-input-number
              v-model="recordForm.cost"
              :min="0"
              :max="99999999"
              :precision="2"
              controls-position="right"
              class="full-width"
            />
          </el-form-item>
        </div>
        <el-form-item label="发生时间">
          <el-date-picker
            v-model="recordForm.occurred_at"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            placeholder="不填写则默认为当前时间"
            class="full-width"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recordVisible = false">取消</el-button>
        <el-button type="primary" :loading="recordSubmitting" @click="submitRecord">
          保存记录
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="completeVisible" title="完成维修" width="560px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="维修结果" required>
          <el-input
            v-model="completeForm.repair_result"
            type="textarea"
            :rows="4"
            maxlength="1000"
            show-word-limit
            placeholder="请填写维修处理结果、更换配件及运行情况"
          />
        </el-form-item>
      </el-form>
      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="提交后工单进入待验收状态，资产仍保持维修中，验收通过后恢复原状态"
      />
      <template #footer>
        <el-button @click="completeVisible = false">取消</el-button>
        <el-button type="primary" :loading="completeSubmitting" @click="submitComplete">
          提交完成
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="acceptVisible" title="验收维修" width="520px">
      <div v-if="detail" class="action-summary">
        <div>
          <span>{{ detail.maintenance_no }} · {{ detail.asset_name }}</span>
          <small>
            维修人 {{ detail.repairer_name || '—' }} · 累计费用
            {{ money(detail.total_cost) }}
          </small>
        </div>
        <el-tag type="warning" effect="light">待验收</el-tag>
      </div>
      <el-form label-position="top">
        <el-form-item label="验收意见">
          <el-input
            v-model="acceptComment"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="选填"
          />
        </el-form-item>
      </el-form>
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        :title="`验收通过后资产将恢复为「${detail?.from_status_label || '原状态'}」，并写入状态历史`"
      />
      <template #footer>
        <el-button @click="acceptVisible = false">取消</el-button>
        <el-button type="primary" :loading="acceptSubmitting" @click="submitAccept">
          确认验收
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

.fault-text {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.muted {
  color: var(--text-3);
}

.inline-tag {
  margin-left: 8px;
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
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 16px;
}

.asset-option {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.4;
}

.asset-option small {
  color: var(--text-3);
  font-size: 11.5px;
}

.flow-steps {
  margin-bottom: 22px;
}

.detail-subtitle {
  margin: 20px 0 10px;
  font-weight: 650;
  color: var(--text-1);
}

.record-card {
  padding: 12px 14px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface-muted);
}

.record-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.record-head strong {
  font-family: var(--font-number);
  color: var(--text-1);
}

.record-card p {
  margin: 0 0 6px;
  color: var(--text-1);
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.record-card small {
  color: var(--text-3);
  font-size: 11.5px;
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

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
