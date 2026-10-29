<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Link, Plus, Refresh, Search, SwitchButton } from '@element-plus/icons-vue'

import { contractApi } from '@/api/contract'
import { useFilterMemory } from '@/composables/useFilterMemory'
import { useFormDraft } from '@/composables/useFormDraft'
import { useAuthStore } from '@/stores/auth'
import type {
  Contract,
  ContractAssetOption,
  ContractDeptOption,
  ContractOwnerOption,
  ContractStatus,
  ContractSummary,
  ContractType,
} from '@/types/contract'
import { CONTRACT_STATUS_OPTIONS, CONTRACT_TYPE_OPTIONS } from '@/types/contract'
import { formatDateTime } from '@/utils/format'

const auth = useAuthStore()
const route = useRoute()

const canCreate = computed(() => auth.hasPerm('asset:contract:create'))

const loading = ref(false)
const rows = ref<Contract[]>([])
const total = ref(0)
const summary = ref<ContractSummary>({
  active_count: 0,
  expiring_count: 0,
  expired_count: 0,
  terminated_count: 0,
  total_amount: 0,
  linked_asset_count: 0,
})
const query = reactive({
  page: 1,
  page_size: 10,
  keyword: '',
  contract_type: undefined as ContractType | undefined,
  status: undefined as ContractStatus | undefined,
})

const filterMemory = useFilterMemory('assets-contracts', query, {
  defaults: {
    page: 1,
    page_size: 10,
    keyword: '',
    contract_type: undefined,
    status: undefined,
  },
})
filterMemory.restore()

const depts = ref<ContractDeptOption[]>([])
const owners = ref<ContractOwnerOption[]>([])

const formVisible = ref(false)
const formMode = ref<'create' | 'edit'>('create')
const formSubmitting = ref(false)
const form = reactive({
  id: undefined as number | undefined,
  version: 1,
  name: '',
  contract_type: 'PURCHASE' as ContractType,
  supplier: '',
  amount: undefined as number | undefined,
  sign_date: '',
  start_date: '',
  end_date: '',
  dept_id: undefined as number | undefined,
  owner_id: undefined as number | undefined,
  remark: '',
})

function resetForm(): void {
  form.id = undefined
  form.version = 1
  form.name = ''
  form.contract_type = 'PURCHASE'
  form.supplier = ''
  form.amount = undefined
  form.sign_date = ''
  form.start_date = ''
  form.end_date = ''
  form.dept_id = undefined
  form.owner_id = undefined
  form.remark = ''
}

const createDraft = useFormDraft('contracts-create', form, {
  isMeaningful: (value) =>
    Boolean(
      value.name.trim() ||
        value.supplier.trim() ||
        value.amount !== undefined ||
        value.start_date ||
        value.end_date ||
        value.remark.trim(),
    ),
})
const formRestored = ref(false)
const draftSavedLabel = computed(() => {
  const savedAt = createDraft.savedAt.value
  if (!savedAt) return ''
  return new Date(savedAt).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
})

function discardCreateDraft(): void {
  createDraft.discard()
  resetForm()
  formRestored.value = false
}

const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<Contract | null>(null)

const linkVisible = ref(false)
const linkLoading = ref(false)
const linkSubmitting = ref(false)
const linkRows = ref<ContractAssetOption[]>([])
const linkTotal = ref(0)
const linkSelected = ref<ContractAssetOption[]>([])
const linkQuery = reactive({ page: 1, page_size: 10, keyword: '' })

const renewVisible = ref(false)
const renewSubmitting = ref(false)
const renewForm = reactive({
  end_date: '',
  amount: undefined as number | undefined,
  remark: '',
})

async function fetchRows(): Promise<void> {
  loading.value = true
  try {
    const page = await contractApi.list({
      page: query.page,
      page_size: query.page_size,
      keyword: query.keyword.trim() || undefined,
      contract_type: query.contract_type,
      status: query.status,
    })
    rows.value = page.items
    total.value = page.total
  } finally {
    loading.value = false
  }
}

async function fetchSummary(): Promise<void> {
  summary.value = await contractApi.summary()
}

async function fetchData(): Promise<void> {
  await Promise.all([fetchRows(), fetchSummary()])
}

async function loadOptions(): Promise<void> {
  try {
    const [deptData, ownerData] = await Promise.all([
      contractApi.departments(),
      contractApi.owners(),
    ])
    depts.value = deptData
    owners.value = ownerData
  } catch {
    depts.value = []
    owners.value = []
  }
}

function handleSearch(): void {
  query.page = 1
  void fetchRows()
}

function resetFilters(): void {
  query.keyword = ''
  query.contract_type = undefined
  query.status = undefined
  query.page = 1
  void fetchRows()
}

function deptLabel(dept: ContractDeptOption): string {
  return `${'— '.repeat(Math.max(dept.level - 1, 0))}${dept.name}`
}

function formatMoney(value: number | string | null | undefined): string {
  return `¥ ${Number(value || 0).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function expiryText(row: Contract): string {
  if (row.status === 'TERMINATED') return '已终止'
  if (row.days_to_expiry < 0) return `已到期 ${-row.days_to_expiry} 天`
  if (row.days_to_expiry === 0) return '今天到期'
  return `剩余 ${row.days_to_expiry} 天`
}

function expiryClass(row: Contract): string {
  if (row.status === 'EXPIRED') return 'expiry-danger'
  if (row.status === 'EXPIRING') return 'expiry-warning'
  return 'expiry-normal'
}

function openCreate(): void {
  formMode.value = 'create'
  resetForm()
  createDraft.start()
  formRestored.value = createDraft.restore()
  formVisible.value = true
  void loadOptions()
}

function openEdit(row: Contract): void {
  createDraft.stop()
  formRestored.value = false
  formMode.value = 'edit'
  form.id = row.id
  form.version = row.version
  form.name = row.name
  form.contract_type = row.contract_type
  form.supplier = row.supplier || ''
  form.amount = Number(row.amount || 0)
  form.sign_date = row.sign_date || ''
  form.start_date = row.start_date
  form.end_date = row.end_date
  form.dept_id = row.dept_id ?? undefined
  form.owner_id = row.owner_id ?? undefined
  form.remark = row.remark || ''
  formVisible.value = true
  void loadOptions()
}

async function submitForm(): Promise<void> {
  if (form.name.trim().length < 2) {
    ElMessage.warning('请填写合同名称，至少 2 个字符')
    return
  }
  if (!form.start_date || !form.end_date) {
    ElMessage.warning('请选择合同开始与结束日期')
    return
  }
  if (form.end_date < form.start_date) {
    ElMessage.warning('合同结束日期不能早于开始日期')
    return
  }
  if (form.sign_date && form.sign_date > form.end_date) {
    ElMessage.warning('签订日期不能晚于结束日期')
    return
  }
  formSubmitting.value = true
  try {
    const payload = {
      name: form.name.trim(),
      contract_type: form.contract_type,
      supplier: form.supplier.trim() || null,
      amount: form.amount ?? 0,
      sign_date: form.sign_date || null,
      start_date: form.start_date,
      end_date: form.end_date,
      dept_id: form.dept_id ?? null,
      owner_id: form.owner_id ?? null,
      remark: form.remark.trim() || null,
    }
    if (formMode.value === 'create') {
      const created = await contractApi.create(payload)
      createDraft.clear()
      ElMessage.success('合同已创建，可在详情中关联资产')
      formVisible.value = false
      await fetchData()
      await openDetail(created.id)
    } else if (form.id) {
      await contractApi.update(form.id, { ...payload, version: form.version })
      ElMessage.success('合同已更新')
      formVisible.value = false
      await fetchData()
      if (detail.value?.id === form.id) {
        await openDetail(form.id)
      }
    }
  } finally {
    formSubmitting.value = false
  }
}

async function openDetail(id: number): Promise<void> {
  detailLoading.value = true
  detailVisible.value = true
  try {
    detail.value = await contractApi.get(id)
  } finally {
    detailLoading.value = false
  }
}

async function refreshDetail(): Promise<void> {
  if (detail.value) {
    detail.value = await contractApi.get(detail.value.id)
  }
}

async function openLink(): Promise<void> {
  if (!detail.value) return
  linkSelected.value = []
  linkQuery.page = 1
  linkQuery.keyword = ''
  linkVisible.value = true
  await loadLinkAssets()
}

async function loadLinkAssets(): Promise<void> {
  if (!detail.value) return
  linkLoading.value = true
  try {
    const page = await contractApi.assets({
      page: linkQuery.page,
      page_size: linkQuery.page_size,
      keyword: linkQuery.keyword.trim() || undefined,
      contract_id: detail.value.id,
    })
    linkRows.value = page.items
    linkTotal.value = page.total
  } finally {
    linkLoading.value = false
  }
}

function handleLinkSelection(selection: ContractAssetOption[]): void {
  linkSelected.value = selection
}

function assetSelectable(row: ContractAssetOption): boolean {
  return !row.linked
}

async function submitLink(): Promise<void> {
  if (!detail.value) return
  if (linkSelected.value.length === 0) {
    ElMessage.warning('请选择需要关联的资产')
    return
  }
  linkSubmitting.value = true
  try {
    detail.value = await contractApi.linkAssets(
      detail.value.id,
      linkSelected.value.map((item) => item.id),
    )
    linkVisible.value = false
    ElMessage.success('资产已关联')
    await fetchData()
  } finally {
    linkSubmitting.value = false
  }
}

async function unlinkAsset(asset: Contract['assets'][number]): Promise<void> {
  if (!detail.value) return
  try {
    await ElMessageBox.confirm(
      `确认解除资产「${asset.name}（${asset.asset_no}）」与该合同的关联？`,
      '解除关联',
      { confirmButtonText: '解除关联', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  detail.value = await contractApi.unlinkAsset(detail.value.id, asset.id)
  ElMessage.success('资产关联已解除')
  await fetchData()
}

function openRenew(): void {
  if (!detail.value) return
  const current = detail.value.end_date
  const next = new Date(current)
  next.setFullYear(next.getFullYear() + 1)
  renewForm.end_date = next.toISOString().slice(0, 10)
  renewForm.amount = Number(detail.value.amount || 0)
  renewForm.remark = ''
  renewVisible.value = true
}

async function openRenewFor(row: Contract): Promise<void> {
  await openDetail(row.id)
  openRenew()
}

async function submitRenew(): Promise<void> {
  if (!detail.value) return
  if (!renewForm.end_date) {
    ElMessage.warning('请选择续签后的结束日期')
    return
  }
  if (renewForm.end_date <= detail.value.end_date) {
    ElMessage.warning('续签后的结束日期必须晚于原结束日期')
    return
  }
  renewSubmitting.value = true
  try {
    detail.value = await contractApi.renew(detail.value.id, {
      version: detail.value.version,
      end_date: renewForm.end_date,
      amount: renewForm.amount ?? undefined,
      remark: renewForm.remark.trim() || undefined,
    })
    renewVisible.value = false
    ElMessage.success('合同已续签')
    await fetchData()
  } finally {
    renewSubmitting.value = false
  }
}

async function terminateContract(target: Contract): Promise<void> {
  let reason = ''
  try {
    const result = await ElMessageBox.prompt(
      '终止后合同将不可继续编辑、续签或关联资产，请填写终止原因。',
      '终止合同',
      {
        confirmButtonText: '确认终止',
        cancelButtonText: '取消',
        inputType: 'textarea',
        inputPlaceholder: '终止原因（至少 2 个字符）',
        inputValidator: (value: string) =>
          value.trim().length >= 2 || '请填写终止原因，至少 2 个字符',
        type: 'warning',
      },
    )
    reason = result.value.trim()
  } catch {
    return
  }
  const updated = await contractApi.terminate(target.id, target.version, reason)
  ElMessage.success('合同已终止')
  if (detail.value?.id === updated.id) {
    detail.value = updated
  }
  await fetchData()
}

onMounted(() => {
  const status = route.query.status
  if (
    typeof status === 'string' &&
    CONTRACT_STATUS_OPTIONS.some((item) => item.value === status)
  ) {
    query.status = status as ContractStatus
  }
  const keyword = route.query.keyword
  if (typeof keyword === 'string' && keyword.trim()) {
    query.keyword = keyword.trim()
  }
  void fetchData()
  void loadOptions()
})
</script>

<template>
  <div class="page contract-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">CONTRACT &amp; WARRANTY</p>
        <h1 class="page-title">合同管理</h1>
        <p class="page-subtitle">
          管理采购、维保与租赁合同，关联资产并跟踪有效期；临近到期自动进入通知中心，续签或终止均写入审计日志。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" :loading="loading" @click="fetchData">刷新</el-button>
        <el-button v-if="canCreate" type="primary" :icon="Plus" @click="openCreate">
          新建合同
        </el-button>
      </div>
    </header>

    <section class="summary-grid">
      <article class="surface-card summary-card">
        <span class="summary-label">生效中</span>
        <strong class="summary-value">{{ summary.active_count }}</strong>
        <small>份合同</small>
      </article>
      <article class="surface-card summary-card is-warning">
        <span class="summary-label">30 天内到期</span>
        <strong class="summary-value">{{ summary.expiring_count }}</strong>
        <small>需安排续签</small>
      </article>
      <article class="surface-card summary-card is-danger">
        <span class="summary-label">已到期</span>
        <strong class="summary-value">{{ summary.expired_count }}</strong>
        <small>待处理</small>
      </article>
      <article class="surface-card summary-card">
        <span class="summary-label">有效合同金额</span>
        <strong class="summary-value">{{ formatMoney(summary.total_amount) }}</strong>
        <small>关联 {{ summary.linked_asset_count }} 项资产</small>
      </article>
    </section>

    <section class="surface-card panel">
      <div class="filter-bar">
        <el-input
          v-model="query.keyword"
          :prefix-icon="Search"
          placeholder="合同编号 / 名称 / 供应商"
          clearable
          class="filter-keyword"
          @keyup.enter="handleSearch"
          @clear="handleSearch"
        />
        <el-select
          v-model="query.contract_type"
          placeholder="合同类型"
          clearable
          class="filter-select"
          @change="handleSearch"
        >
          <el-option
            v-for="item in CONTRACT_TYPE_OPTIONS"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-select
          v-model="query.status"
          placeholder="合同状态"
          clearable
          class="filter-select"
          @change="handleSearch"
        >
          <el-option
            v-for="item in CONTRACT_STATUS_OPTIONS"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <div class="filter-actions">
          <el-button :icon="Search" @click="handleSearch">查询</el-button>
          <el-button text @click="resetFilters">重置</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="rows" row-key="id" empty-text="当前没有合同">
        <el-table-column label="合同" min-width="230">
          <template #default="{ row }">
            <div class="stack-cell">
              <el-button link type="primary" class="contract-link" @click="openDetail(row.id)">
                {{ row.name }}
              </el-button>
              <small class="mono">{{ row.contract_no }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="110">
          <template #default="{ row }">
            <el-tag :type="row.contract_type_tag_type" effect="plain" size="small">
              {{ row.contract_type_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="供应商" min-width="150">
          <template #default="{ row }">{{ row.supplier || '—' }}</template>
        </el-table-column>
        <el-table-column label="合同金额" width="140" align="right">
          <template #default="{ row }">
            <span class="mono">{{ formatMoney(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="有效期" min-width="190">
          <template #default="{ row }">
            <div class="stack-cell">
              <span class="mono">{{ row.start_date }} ~ {{ row.end_date }}</span>
              <small :class="expiryClass(row)">{{ expiryText(row) }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="关联资产" width="100" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetail(row.id)">
              {{ row.asset_count }} 项
            </el-button>
          </template>
        </el-table-column>
        <el-table-column label="部门 / 负责人" min-width="170">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.dept_name || '公司级' }}</span>
              <small>{{ row.owner_name || '未指定负责人' }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.status_tag_type" effect="light">
              {{ row.status_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="openDetail(row.id)">详情</el-button>
              <el-button v-if="row.can_edit" link type="primary" @click="openEdit(row)">
                编辑
              </el-button>
              <el-button v-if="row.can_renew" link type="success" @click="openRenewFor(row)">
                续签
              </el-button>
              <el-button
                v-if="row.can_terminate"
                link
                type="danger"
                @click="terminateContract(row)"
              >
                终止
              </el-button>
            </div>
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

    <el-dialog
      v-model="formVisible"
      :title="formMode === 'create' ? '新建合同' : '编辑合同'"
      width="820px"
      destroy-on-close
      @closed="createDraft.stop()"
    >
      <el-alert
        v-if="formRestored"
        type="info"
        :closable="false"
        show-icon
        class="draft-alert"
      >
        <template #title>
          已恢复 {{ draftSavedLabel }} 保存的草稿
          <el-button link type="primary" size="small" @click="discardCreateDraft">
            放弃草稿
          </el-button>
        </template>
      </el-alert>
      <el-form label-position="top">
        <div class="form-grid">
          <el-form-item label="合同名称" class="grid-span-2">
            <el-input v-model="form.name" maxlength="160" placeholder="例如 2026 年度办公设备维保合同" />
          </el-form-item>
          <el-form-item label="合同类型">
            <el-select v-model="form.contract_type" class="full-width">
              <el-option
                v-for="item in CONTRACT_TYPE_OPTIONS"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="供应商 / 对方单位">
            <el-input v-model="form.supplier" maxlength="160" placeholder="选填" />
          </el-form-item>
          <el-form-item label="合同金额（元）">
            <el-input-number
              v-model="form.amount"
              :min="0"
              :precision="2"
              :step="1000"
              controls-position="right"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="签订日期">
            <el-date-picker
              v-model="form.sign_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="选填"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="开始日期">
            <el-date-picker
              v-model="form.start_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="必填"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker
              v-model="form.end_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="必填"
              class="full-width"
            />
          </el-form-item>
          <el-form-item label="所属部门">
            <el-select
              v-model="form.dept_id"
              clearable
              filterable
              placeholder="不选视为公司级合同"
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
          <el-form-item label="合同负责人">
            <el-select
              v-model="form.owner_id"
              clearable
              filterable
              placeholder="选填"
              class="full-width"
            >
              <el-option
                v-for="owner in owners"
                :key="owner.id"
                :label="owner.dept_name ? `${owner.name} · ${owner.dept_name}` : owner.name"
                :value="owner.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="备注" class="grid-span-3">
            <el-input
              v-model="form.remark"
              type="textarea"
              :rows="3"
              maxlength="500"
              show-word-limit
              placeholder="选填"
            />
          </el-form-item>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">取消</el-button>
        <el-button type="primary" :loading="formSubmitting" @click="submitForm">
          {{ formMode === 'create' ? '创建合同' : '保存修改' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="detailVisible"
      :title="detail ? `${detail.contract_no} · ${detail.name}` : '合同详情'"
      width="1000px"
      destroy-on-close
    >
      <div v-loading="detailLoading">
        <template v-if="detail">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="合同编号">
              <span class="mono">{{ detail.contract_no }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="detail.status_tag_type" effect="light">
                {{ detail.status_label }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="合同类型">
              {{ detail.contract_type_label }}
            </el-descriptions-item>
            <el-descriptions-item label="供应商">
              {{ detail.supplier || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="合同金额">
              <span class="mono">{{ formatMoney(detail.amount) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="关联资产">
              {{ detail.asset_count }} 项
            </el-descriptions-item>
            <el-descriptions-item label="签订日期">
              {{ detail.sign_date || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="有效期">
              <span class="mono">{{ detail.start_date }} ~ {{ detail.end_date }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="到期情况">
              <span :class="expiryClass(detail)">{{ expiryText(detail) }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="所属部门">
              {{ detail.dept_name || '公司级' }}
            </el-descriptions-item>
            <el-descriptions-item label="负责人">
              {{ detail.owner_name || '未指定负责人' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建人">
              {{ detail.created_by_name || '—' }}
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDateTime(detail.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="备注" :span="2">
              {{ detail.remark || '—' }}
            </el-descriptions-item>
            <el-descriptions-item
              v-if="detail.status === 'TERMINATED'"
              label="终止原因"
              :span="2"
            >
              {{ detail.terminate_reason || '—' }}
              <small v-if="detail.terminated_at" class="terminated-at">
                （{{ formatDateTime(detail.terminated_at) }}）
              </small>
            </el-descriptions-item>
          </el-descriptions>

          <div class="detail-subtitle">
            <span>关联资产</span>
            <el-button
              v-if="detail.can_link_asset"
              size="small"
              type="primary"
              plain
              :icon="Link"
              @click="openLink"
            >
              关联资产
            </el-button>
          </div>
          <el-table :data="detail.assets" size="small" border empty-text="暂未关联资产">
            <el-table-column label="资产编号" width="160">
              <template #default="{ row }">
                <span class="mono">{{ row.asset_no }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="资产名称" min-width="160" />
            <el-table-column label="分类 / 型号" min-width="150">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.category_name || '未分类' }}</span>
                  <small>{{ row.model_name || '—' }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="使用人 / 部门" min-width="130">
              <template #default="{ row }">
                <div class="stack-cell">
                  <span>{{ row.custodian_name || '未指定' }}</span>
                  <small>{{ row.dept_name || '未指定部门' }}</small>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="status_label" label="状态" width="100" />
            <el-table-column label="关联时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.linked_at) }}</template>
            </el-table-column>
            <el-table-column v-if="detail.can_link_asset" label="操作" width="90">
              <template #default="{ row }">
                <el-button link type="danger" @click="unlinkAsset(row)">解除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="detail-actions">
            <el-button
              v-if="detail.can_edit"
              :icon="SwitchButton"
              @click="openEdit(detail)"
            >
              编辑
            </el-button>
            <el-button v-if="detail.can_renew" type="success" plain @click="openRenew">
              续签
            </el-button>
            <el-button
              v-if="detail.can_terminate"
              type="danger"
              plain
              @click="terminateContract(detail)"
            >
              终止合同
            </el-button>
            <el-button @click="detailVisible = false">关闭</el-button>
          </div>
        </template>
      </div>
    </el-dialog>

    <el-dialog v-model="linkVisible" title="关联资产" width="920px" destroy-on-close>
      <div class="filter-bar">
        <el-input
          v-model="linkQuery.keyword"
          :prefix-icon="Search"
          placeholder="搜索资产编号 / 名称 / 序列号"
          clearable
          class="filter-keyword"
          @keyup.enter="linkQuery.page = 1; loadLinkAssets()"
          @clear="linkQuery.page = 1; loadLinkAssets()"
        />
        <div class="filter-actions">
          <el-button :icon="Search" @click="linkQuery.page = 1; loadLinkAssets()">
            查询
          </el-button>
        </div>
      </div>
      <el-table
        v-loading="linkLoading"
        :data="linkRows"
        row-key="id"
        border
        empty-text="没有可关联的资产"
        @selection-change="handleLinkSelection"
      >
        <el-table-column type="selection" width="48" :selectable="assetSelectable" />
        <el-table-column label="资产编号" width="160">
          <template #default="{ row }">
            <span class="mono">{{ row.asset_no }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="资产名称" min-width="160" />
        <el-table-column label="分类 / 型号" min-width="150">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.category_name || '未分类' }}</span>
              <small>{{ row.model_name || '—' }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="部门 / 使用人" min-width="130">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.dept_name || '未指定部门' }}</span>
              <small>{{ row.custodian_name || '未指定使用人' }}</small>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.linked" size="small" type="info" effect="plain">
              已关联
            </el-tag>
            <span v-else>{{ row.status_label }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-footer">
        <el-pagination
          v-model:current-page="linkQuery.page"
          v-model:page-size="linkQuery.page_size"
          :total="linkTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @current-change="loadLinkAssets"
          @size-change="linkQuery.page = 1; loadLinkAssets()"
        />
      </div>
      <template #footer>
        <span class="link-selected">已选择 {{ linkSelected.length }} 项资产</span>
        <el-button @click="linkVisible = false">取消</el-button>
        <el-button type="primary" :loading="linkSubmitting" @click="submitLink">
          确认关联
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="renewVisible" title="续签合同" width="520px" destroy-on-close>
      <el-form label-position="top">
        <el-form-item label="原结束日期">
          <span class="mono">{{ detail?.end_date || '—' }}</span>
        </el-form-item>
        <el-form-item label="续签后结束日期">
          <el-date-picker
            v-model="renewForm.end_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择新的结束日期"
            class="full-width"
          />
        </el-form-item>
        <el-form-item label="合同金额（元，可选）">
          <el-input-number
            v-model="renewForm.amount"
            :min="0"
            :precision="2"
            :step="1000"
            controls-position="right"
            class="full-width"
          />
        </el-form-item>
        <el-form-item label="续签备注（可选）">
          <el-input
            v-model="renewForm.remark"
            type="textarea"
            :rows="2"
            maxlength="500"
            placeholder="例如 续签一年，金额不变"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renewVisible = false">取消</el-button>
        <el-button type="primary" :loading="renewSubmitting" @click="submitRenew">
          确认续签
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

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 16px;
}

.summary-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 16px 18px;
}

.summary-label {
  color: var(--text-3);
  font-size: 12px;
  letter-spacing: 0.04em;
}

.summary-value {
  font-family: var(--font-number);
  font-size: 26px;
  font-weight: 700;
  color: var(--text-1);
}

.summary-card small {
  color: var(--text-3);
  font-size: 12px;
}

.summary-card.is-warning .summary-value {
  color: var(--warning-6, #e6a23c);
}

.summary-card.is-danger .summary-value {
  color: var(--danger-6, #f56c6c);
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

.contract-link {
  font-weight: 650;
  justify-content: flex-start;
  padding: 0;
  height: auto;
}

.row-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.expiry-normal {
  color: var(--text-3);
  font-size: 11.5px;
}

.expiry-warning {
  color: var(--warning-6, #e6a23c);
  font-size: 11.5px;
  font-weight: 600;
}

.expiry-danger {
  color: var(--danger-6, #f56c6c);
  font-size: 11.5px;
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

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 16px;
}

.grid-span-2 {
  grid-column: span 2;
}

.grid-span-3 {
  grid-column: span 3;
}

.detail-subtitle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 20px 0 10px;
  font-weight: 650;
  color: var(--text-1);
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.terminated-at {
  color: var(--text-3);
  font-size: 12px;
}

.link-selected {
  float: left;
  line-height: 32px;
  color: var(--text-3);
  font-size: 13px;
}

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .filter-keyword {
    width: 100%;
  }

  .filter-actions {
    margin-left: 0;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .grid-span-2,
  .grid-span-3 {
    grid-column: span 1;
  }
}

.draft-alert {
  margin-bottom: 14px;
}

.draft-alert :deep(.el-alert__title) {
  display: flex;
  align-items: center;
  gap: 6px;
}
</style>
