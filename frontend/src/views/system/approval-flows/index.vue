<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  ArrowDown,
  ArrowUp,
  Delete,
  Plus,
  Refresh,
  Search,
  Share,
} from '@element-plus/icons-vue'

import { approvalFlowApi } from '@/api/approvalFlow'
import { useAuthStore } from '@/stores/auth'
import type {
  ApprovalFlowItem,
  ApprovalFlowNode,
  ApprovalFlowNodeInput,
  ApprovalFlowOptions,
  ApprovalFlowPayload,
  ApproverType,
  FlowRoleOption,
  FlowUserOption,
} from '@/types/approvalFlow'
import {
  APPROVER_TYPE_OPTIONS,
  FALLBACK_OPTIONS,
  MANAGER_LEVEL_OPTIONS,
  managerLevelLabel,
} from '@/types/approvalFlow'
import { formatDateTime } from '@/utils/format'

const auth = useAuthStore()
const canManage = computed(() => auth.hasPerm('asset:request:flow:manage'))

const loading = ref(false)
const flows = ref<ApprovalFlowItem[]>([])
const keyword = ref('')

const filteredFlows = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  if (!query) return flows.value
  return flows.value.filter((flow) => {
    const haystack = [
      flow.name,
      flow.description ?? '',
      ...flow.dept_names,
      ...flow.nodes.map((node) => node.name),
    ]
      .join(' ')
      .toLowerCase()
    return haystack.includes(query)
  })
})

const enabledCount = computed(
  () => flows.value.filter((flow) => flow.status === 1).length,
)
const defaultFlow = computed(
  () => flows.value.find((flow) => flow.is_default) ?? null,
)

function deptSummary(flow: ApprovalFlowItem): string {
  if (!flow.dept_names.length) {
    return flow.is_default ? '未单独绑定部门的全部范围' : '未绑定部门'
  }
  if (flow.dept_names.length <= 3) return flow.dept_names.join('、')
  return `${flow.dept_names.slice(0, 3).join('、')} 等 ${flow.dept_names.length} 个部门`
}

function nodeApproverLabel(node: ApprovalFlowNode): string {
  if (node.approver_type === 'DEPT_MANAGER') {
    return managerLevelLabel(node.manager_level)
  }
  if (node.approver_type === 'USER') return node.user_name || '指定用户'
  return node.role_name || node.role_code || '指定角色'
}

function nodeMetaText(node: ApprovalFlowNode): string {
  const modeLabel = node.approve_mode === 'ALL' ? '会签' : '或签'
  return `${nodeApproverLabel(node)} · ${modeLabel}`
}

function nodeTooltip(node: ApprovalFlowNode): string {
  return `第 ${node.step_no} 级「${node.name}」：${nodeApproverLabel(node)}，${
    node.approve_mode === 'ALL' ? '全部通过后流转' : '一人通过即流转'
  }；找不到审批人时${node.fallback_type_label}`
}

async function loadFlows(): Promise<void> {
  loading.value = true
  try {
    flows.value = await approvalFlowApi.list()
  } finally {
    loading.value = false
  }
}

const statusLoadingId = ref<number | null>(null)

async function toggleStatus(flow: ApprovalFlowItem, value: string | number | boolean): Promise<void> {
  if (statusLoadingId.value !== null) return
  statusLoadingId.value = flow.id
  try {
    const status = Boolean(value) ? 1 : 0
    await approvalFlowApi.updateStatus(flow.id, { status, version: flow.version })
    ElMessage.success(status === 1 ? `流程「${flow.name}」已启用` : `流程「${flow.name}」已停用`)
    await loadFlows()
  } catch {
    // 版本冲突等错误已由请求层提示，刷新保持最新状态
    await loadFlows()
  } finally {
    statusLoadingId.value = null
  }
}

const options = reactive<ApprovalFlowOptions>({
  departments: [],
  users: [],
  roles: [],
})
const optionsLoading = ref(false)

function selectedUserIds(): Set<number> {
  return new Set(
    flowForm.nodes
      .map((node) => node.user_id)
      .filter((id): id is number => typeof id === 'number'),
  )
}

function mergeUsers(incoming: FlowUserOption[]): void {
  const keep = selectedUserIds()
  const merged = new Map<number, FlowUserOption>()
  for (const user of options.users) {
    if (keep.has(user.id)) merged.set(user.id, user)
  }
  for (const user of incoming) merged.set(user.id, user)
  options.users = Array.from(merged.values())
}

function mergeRoles(incoming: FlowRoleOption[]): void {
  const merged = new Map<string, FlowRoleOption>()
  for (const role of incoming) merged.set(role.code, role)
  for (const role of options.roles) merged.set(role.code, role)
  options.roles = Array.from(merged.values())
}

async function loadOptions(search?: string): Promise<void> {
  optionsLoading.value = true
  try {
    const data = await approvalFlowApi.options(search)
    options.departments = data.departments
    mergeUsers(data.users)
    mergeRoles(data.roles)
  } finally {
    optionsLoading.value = false
  }
}

let userSearchTimer: ReturnType<typeof setTimeout> | null = null

function handleUserSearch(query: string): void {
  if (userSearchTimer) clearTimeout(userSearchTimer)
  userSearchTimer = setTimeout(() => {
    void loadOptions(query.trim() || undefined)
  }, 300)
}

function emptyNode(): ApprovalFlowNodeInput {
  return {
    name: '',
    approver_type: 'DEPT_MANAGER',
    user_id: null,
    role_code: null,
    manager_level: 1,
    approve_mode: 'OR',
    fallback_type: 'ASSET_ADMIN',
  }
}

interface FlowFormState {
  id: number | null
  name: string
  description: string
  is_default: boolean
  status: number
  dept_ids: number[]
  nodes: ApprovalFlowNodeInput[]
  version: number
}

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const submitting = ref(false)
const formRef = ref<FormInstance>()

const flowForm = reactive<FlowFormState>({
  id: null,
  name: '',
  description: '',
  is_default: false,
  status: 1,
  dept_ids: [],
  nodes: [emptyNode()],
  version: 1,
})

const formRules: FormRules = {
  name: [
    { required: true, message: '请输入流程名称', trigger: 'blur' },
    { min: 2, max: 80, message: '流程名称需为 2-80 个字符', trigger: 'blur' },
  ],
}

function resetForm(): void {
  Object.assign(flowForm, {
    id: null,
    name: '',
    description: '',
    is_default: false,
    status: 1,
    dept_ids: [],
    nodes: [emptyNode()],
    version: 1,
  })
  formRef.value?.clearValidate()
}

async function openCreate(): Promise<void> {
  resetForm()
  dialogMode.value = 'create'
  dialogVisible.value = true
  await loadOptions()
}

async function openEdit(flow: ApprovalFlowItem): Promise<void> {
  resetForm()
  dialogMode.value = 'edit'
  Object.assign(flowForm, {
    id: flow.id,
    name: flow.name,
    description: flow.description ?? '',
    is_default: flow.is_default,
    status: flow.status,
    dept_ids: [...flow.dept_ids],
    version: flow.version,
    nodes: flow.nodes.map((node) => ({
      name: node.name,
      approver_type: node.approver_type,
      user_id: node.user_id,
      role_code: node.role_code,
      manager_level: node.manager_level,
      approve_mode: node.approve_mode,
      fallback_type: node.fallback_type,
    })),
  })
  await loadOptions()
  for (const node of flow.nodes) {
    if (node.user_id && node.user_name) {
      options.users = [
        {
          id: node.user_id,
          username: node.user_name,
          real_name: node.user_name,
          dept_id: null,
          dept_name: null,
          status: 1,
        },
        ...options.users.filter((user) => user.id !== node.user_id),
      ]
    }
    if (node.role_code) {
      options.roles = [
        {
          code: node.role_code,
          name: node.role_name || node.role_code,
          data_scope: '',
        },
        ...options.roles.filter((role) => role.code !== node.role_code),
      ]
    }
  }
  dialogVisible.value = true
}

function addNode(): void {
  if (flowForm.nodes.length >= 10) {
    ElMessage.warning('审批节点最多配置 10 级')
    return
  }
  flowForm.nodes.push(emptyNode())
}

function removeNode(index: number): void {
  if (flowForm.nodes.length <= 1) {
    ElMessage.warning('审批流程至少需要 1 个节点')
    return
  }
  flowForm.nodes.splice(index, 1)
}

function moveNode(index: number, delta: number): void {
  const target = index + delta
  if (target < 0 || target >= flowForm.nodes.length) return
  const [node] = flowForm.nodes.splice(index, 1)
  flowForm.nodes.splice(target, 0, node)
}

function handleApproverTypeChange(node: ApprovalFlowNodeInput): void {
  if (node.approver_type !== 'USER') node.user_id = null
  if (node.approver_type !== 'ROLE') node.role_code = null
  if (node.approver_type !== 'DEPT_MANAGER') node.manager_level = 1
}

function validateNodes(): boolean {
  for (const [index, node] of flowForm.nodes.entries()) {
    const label = `第 ${index + 1} 级`
    if (!node.name.trim()) {
      ElMessage.warning(`${label}审批节点的名称不能为空`)
      return false
    }
    if (node.approver_type === 'USER' && !node.user_id) {
      ElMessage.warning(`${label}审批节点请选择指定用户`)
      return false
    }
    if (node.approver_type === 'ROLE' && !node.role_code) {
      ElMessage.warning(`${label}审批节点请选择指定角色`)
      return false
    }
  }
  return true
}

function buildPayload(): ApprovalFlowPayload {
  return {
    name: flowForm.name.trim(),
    description: flowForm.description.trim() || null,
    is_default: flowForm.is_default,
    status: flowForm.status,
    dept_ids: [...flowForm.dept_ids],
    nodes: flowForm.nodes.map((node) => ({
      name: node.name.trim(),
      approver_type: node.approver_type,
      user_id: node.approver_type === 'USER' ? node.user_id : null,
      role_code: node.approver_type === 'ROLE' ? node.role_code : null,
      manager_level: node.approver_type === 'DEPT_MANAGER' ? node.manager_level : 1,
      approve_mode: node.approve_mode,
      fallback_type: node.fallback_type,
    })),
  }
}

async function submitFlow(): Promise<void> {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid || !validateNodes()) return
  if (submitting.value) return
  submitting.value = true
  try {
    const payload = buildPayload()
    if (dialogMode.value === 'create') {
      await approvalFlowApi.create(payload)
      ElMessage.success(`审批流程「${payload.name}」已创建`)
    } else if (flowForm.id !== null) {
      await approvalFlowApi.update(flowForm.id, {
        ...payload,
        version: flowForm.version,
      })
      ElMessage.success(`审批流程「${payload.name}」已更新`)
    }
    dialogVisible.value = false
    await loadFlows()
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void loadFlows()
  void loadOptions()
})
</script>

<template>
  <div class="page flow-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">APPROVAL WORKFLOW</p>
        <h1 class="page-title">审批流程配置</h1>
        <p class="page-subtitle">
          按申请人所属部门自动匹配审批流程，逐级流转；每级可使用部门负责人、指定用户或指定角色审批。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Refresh" :loading="loading" @click="loadFlows">刷新</el-button>
        <el-button
          v-if="canManage"
          type="primary"
          :icon="Plus"
          @click="openCreate"
        >
          新增流程
        </el-button>
      </div>
    </header>

    <section class="surface-card flow-guide">
      <span class="guide-icon"><el-icon><Share /></el-icon></span>
      <div>
        <strong>部门匹配顺序</strong>
        <p>
          申请人所属部门 → 逐级上级部门 → 全局默认流程 → 系统原有审批设置。流程配置仅影响新提交的单据，在途单据按提交时的流程快照继续流转。
        </p>
      </div>
    </section>

    <section class="summary-strip">
      <div class="summary-card surface-card">
        <span>流程总数</span>
        <strong>{{ flows.length }}</strong>
      </div>
      <div class="summary-card surface-card">
        <span>启用流程</span>
        <strong>{{ enabledCount }}</strong>
      </div>
      <div class="summary-card surface-card">
        <span>全局默认</span>
        <strong class="summary-name">{{ defaultFlow?.name || '未设置' }}</strong>
        <small>部门专属流程优先于默认流程</small>
      </div>
      <div class="summary-note">
        <span>审批方式</span>
        <small>
          或签：任一审批人通过即流转；会签：全部审批人通过后流转。找不到审批人时按节点兜底策略处理。
        </small>
      </div>
    </section>

    <section class="surface-card panel">
      <div class="filter-bar">
        <el-input
          v-model="keyword"
          :prefix-icon="Search"
          placeholder="搜索流程名称 / 部门 / 节点"
          clearable
          class="filter-keyword"
        />
        <span class="filter-hint">共 {{ filteredFlows.length }} 个流程</span>
      </div>

      <el-table
        v-loading="loading"
        :data="filteredFlows"
        row-key="id"
        empty-text="暂无审批流程，未配置流程的部门将继续沿用系统原有审批设置"
      >
        <el-table-column label="流程名称" min-width="220">
          <template #default="{ row }">
            <div class="stack-cell">
              <span class="flow-name">
                {{ row.name }}
                <el-tag v-if="row.is_default" type="primary" effect="light" size="small">
                  全局默认
                </el-tag>
                <el-tag
                  v-if="row.status === 0"
                  type="info"
                  effect="plain"
                  size="small"
                >
                  已停用
                </el-tag>
              </span>
              <small>{{ row.description || '未填写流程说明' }}</small>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="适用部门" min-width="230">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ deptSummary(row) }}</span>
              <small>{{ row.dept_names.length }} 个部门单独绑定</small>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="审批节点" min-width="300">
          <template #default="{ row }">
            <div class="node-flow">
              <div
                v-for="node in row.nodes"
                :key="node.id"
                class="node-chip"
                :title="nodeTooltip(node)"
              >
                <span class="node-order">{{ node.step_no }}</span>
                <span class="node-copy">
                  <strong>{{ node.name }}</strong>
                  <small>{{ nodeMetaText(node) }}</small>
                </span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <el-switch
              v-if="canManage"
              :model-value="row.status === 1"
              :loading="statusLoadingId === row.id"
              :disabled="statusLoadingId !== null && statusLoadingId !== row.id"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
              @change="toggleStatus(row, $event)"
            />
            <el-tag v-else :type="row.status === 1 ? 'success' : 'info'" effect="light">
              {{ row.status_label }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="最近更新" width="170">
          <template #default="{ row }">
            <div class="stack-cell">
              <span>{{ row.updated_by_name || '—' }}</span>
              <small>{{ formatDateTime(row.updated_at) }}</small>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="canManage"
              link
              type="primary"
              @click="openEdit(row)"
            >
              编辑
            </el-button>
            <span v-else class="muted">只读</span>
          </template>
        </el-table-column>
      </el-table>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增审批流程' : '编辑审批流程'"
      width="820px"
      top="6vh"
      :close-on-click-modal="false"
      @closed="resetForm"
    >
      <el-form
        ref="formRef"
        :model="flowForm"
        :rules="formRules"
        label-position="top"
      >
        <div class="form-grid">
          <el-form-item label="流程名称" prop="name">
            <el-input
              v-model="flowForm.name"
              maxlength="80"
              placeholder="例如：研发中心资产领用审批"
            />
          </el-form-item>
          <el-form-item label="流程状态">
            <el-switch
              v-model="flowForm.status"
              :active-value="1"
              :inactive-value="0"
              inline-prompt
              active-text="启用"
              inactive-text="停用"
            />
          </el-form-item>

          <el-form-item label="适用部门" class="span-2">
            <el-select
              v-model="flowForm.dept_ids"
              multiple
              filterable
              clearable
              collapse-tags
              collapse-tags-tooltip
              :loading="optionsLoading"
              placeholder="不选择则仅作为全局默认流程"
            >
              <el-option
                v-for="dept in options.departments"
                :key="dept.id"
                :label="dept.path || dept.name"
                :value="dept.id"
              >
                <div class="dept-option">
                  <span>{{ dept.path || dept.name }}</span>
                  <small>
                    {{ dept.manager_name ? `负责人：${dept.manager_name}` : '未设置负责人' }}
                  </small>
                </div>
              </el-option>
            </el-select>
            <p class="field-hint">
              一个部门只能绑定一个流程；绑定后该部门及其未单独绑定流程的下级部门都会匹配此流程。
            </p>
          </el-form-item>

          <el-form-item label="全局默认流程" class="span-2">
            <div class="inline-field">
              <el-switch v-model="flowForm.is_default" inline-prompt active-text="是" inactive-text="否" />
              <span class="field-hint">
                设为默认后会自动取消其他流程的默认标记；部门专属流程优先于默认流程。
              </span>
            </div>
          </el-form-item>

          <el-form-item label="流程说明" class="span-2">
            <el-input
              v-model="flowForm.description"
              type="textarea"
              :rows="2"
              maxlength="255"
              show-word-limit
              placeholder="说明该流程的适用范围，便于后续维护"
            />
          </el-form-item>
        </div>

        <div class="node-editor-head">
          <div>
            <strong>审批节点</strong>
            <small>按从上到下的顺序逐级流转，最多 10 级</small>
          </div>
          <el-button
            size="small"
            :icon="Plus"
            :disabled="flowForm.nodes.length >= 10"
            @click="addNode"
          >
            新增节点
          </el-button>
        </div>

        <div class="node-editor">
          <div
            v-for="(node, index) in flowForm.nodes"
            :key="index"
            class="node-card"
          >
            <div class="node-card-head">
              <span class="node-card-order">第 {{ index + 1 }} 级</span>
              <div class="node-card-tools">
                <el-button
                  link
                  :icon="ArrowUp"
                  :disabled="index === 0"
                  aria-label="上移"
                  @click="moveNode(index, -1)"
                />
                <el-button
                  link
                  :icon="ArrowDown"
                  :disabled="index === flowForm.nodes.length - 1"
                  aria-label="下移"
                  @click="moveNode(index, 1)"
                />
                <el-button
                  link
                  type="danger"
                  :icon="Delete"
                  :disabled="flowForm.nodes.length <= 1"
                  aria-label="删除节点"
                  @click="removeNode(index)"
                />
              </div>
            </div>

            <div class="node-grid">
              <el-form-item label="节点名称">
                <el-input
                  v-model="node.name"
                  maxlength="50"
                  placeholder="例如：部门负责人审批"
                />
              </el-form-item>

              <el-form-item label="审批人类型">
                <el-select
                  v-model="node.approver_type"
                  @change="handleApproverTypeChange(node)"
                >
                  <el-option
                    v-for="option in APPROVER_TYPE_OPTIONS"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>

              <el-form-item
                v-if="node.approver_type === 'DEPT_MANAGER'"
                label="负责人层级"
              >
                <el-select v-model="node.manager_level">
                  <el-option
                    v-for="option in MANAGER_LEVEL_OPTIONS"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>

              <el-form-item v-else-if="node.approver_type === 'USER'" label="指定用户">
                <el-select
                  v-model="node.user_id"
                  filterable
                  remote
                  clearable
                  :remote-method="handleUserSearch"
                  :loading="optionsLoading"
                  placeholder="输入姓名 / 用户名搜索"
                >
                  <el-option
                    v-for="user in options.users"
                    :key="user.id"
                    :label="`${user.real_name}（${user.username}）`"
                    :value="user.id"
                  >
                    <div class="user-option">
                      <span>{{ user.real_name }}（{{ user.username }}）</span>
                      <small>{{ user.dept_name || '未分配部门' }}</small>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>

              <el-form-item v-else label="指定角色">
                <el-select v-model="node.role_code" filterable clearable placeholder="请选择角色">
                  <el-option
                    v-for="role in options.roles"
                    :key="role.code"
                    :label="`${role.name}（${role.code}）`"
                    :value="role.code"
                  />
                </el-select>
              </el-form-item>

              <el-form-item label="审批方式">
                <el-radio-group v-model="node.approve_mode">
                  <el-radio-button value="OR">或签</el-radio-button>
                  <el-radio-button value="ALL">会签</el-radio-button>
                </el-radio-group>
              </el-form-item>

              <el-form-item label="找不到审批人时">
                <el-select v-model="node.fallback_type">
                  <el-option
                    v-for="option in FALLBACK_OPTIONS"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </el-form-item>
            </div>

            <p class="node-hint">
              <template v-if="node.approver_type === 'DEPT_MANAGER'">
                按申请人所属部门向上取{{ managerLevelLabel(node.manager_level) }}；负责人未设置或与申请人相同时按兜底策略处理。
              </template>
              <template v-else-if="node.approver_type === 'USER'">
                固定由指定用户审批；用户停用或删除时按兜底策略处理。
              </template>
              <template v-else>
                由拥有该角色且数据范围覆盖申请人部门的用户审批，可能产生多名候选审批人。
              </template>
            </p>
          </div>
        </div>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitFlow">
          {{ dialogMode === 'create' ? '创建流程' : '保存修改' }}
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

.flow-guide {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
  margin-bottom: 16px;
  border-color: color-mix(in srgb, var(--brand) 20%, var(--border));
  background: var(--brand-soft);
}

.guide-icon {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 10px;
  background: var(--surface);
  color: var(--brand);
  font-size: 17px;
}

.flow-guide strong {
  color: var(--text-1);
  font-size: 13.5px;
}

.flow-guide p {
  margin-top: 3px;
  color: var(--text-2);
  font-size: 12.5px;
  line-height: 1.65;
}

.summary-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) 1.6fr;
  gap: 14px;
  margin-bottom: 18px;
}

.summary-card,
.summary-note {
  padding: 16px 18px;
}

.summary-card span,
.summary-note span {
  color: var(--text-3);
  font-size: 12px;
}

.summary-card strong {
  display: block;
  margin-top: 6px;
  font-family: var(--font-number);
  font-size: 24px;
  color: var(--text-1);
}

.summary-name {
  overflow: hidden;
  font-family: inherit !important;
  font-size: 17px !important;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.summary-card small {
  display: block;
  margin-top: 4px;
  color: var(--text-3);
  font-size: 11.5px;
}

.summary-note {
  border-radius: var(--radius-lg);
  border: 1px dashed var(--border-strong);
  background: var(--surface-muted);
}

.summary-note small {
  display: block;
  margin-top: 8px;
  color: var(--text-2);
  font-size: 12px;
  line-height: 1.65;
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

.filter-hint {
  color: var(--text-3);
  font-size: 12px;
}

.stack-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.stack-cell > span {
  color: var(--text-1);
  font-size: 13px;
}

.stack-cell small {
  color: var(--text-3);
  font-size: 11.5px;
}

.flow-name {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}

.node-flow {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.node-chip {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.node-order {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  border-radius: 7px;
  background: var(--brand-soft);
  color: var(--brand);
  font-family: var(--font-number);
  font-size: 11px;
  font-weight: 600;
}

.node-copy {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.node-copy strong {
  overflow: hidden;
  color: var(--text-1);
  font-size: 12.5px;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-copy small {
  overflow: hidden;
  color: var(--text-3);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.muted {
  color: var(--text-3);
  font-size: 12px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0 16px;
}

.span-2 {
  grid-column: span 2;
}

.form-grid :deep(.el-select) {
  width: 100%;
}

.dept-option,
.user-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.dept-option small,
.user-option small {
  color: var(--text-3);
  font-size: 11px;
}

.field-hint {
  margin: 4px 0 0;
  color: var(--text-3);
  font-size: 11.5px;
  line-height: 1.6;
}

.inline-field {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.inline-field .field-hint {
  margin: 0;
}

.node-editor-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 6px 0 10px;
  padding-top: 14px;
  border-top: 1px dashed var(--border);
}

.node-editor-head strong {
  display: block;
  color: var(--text-1);
  font-size: 13.5px;
}

.node-editor-head small {
  display: block;
  margin-top: 2px;
  color: var(--text-3);
  font-size: 11.5px;
}

.node-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 52vh;
  overflow-y: auto;
  padding-right: 2px;
}

.node-card {
  padding: 12px 14px 6px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface-muted);
}

.node-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.node-card-order {
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--brand-soft);
  color: var(--brand);
  font-size: 11px;
  font-weight: 600;
}

.node-card-tools {
  display: flex;
  gap: 2px;
}

.node-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0 14px;
}

.node-grid :deep(.el-select) {
  width: 100%;
}

.node-grid :deep(.el-form-item) {
  margin-bottom: 10px;
}

.node-hint {
  margin: 0 0 8px;
  color: var(--text-3);
  font-size: 11px;
  line-height: 1.6;
}

:deep(.flow-page .el-dialog) {
  max-width: 94vw;
}

@media (max-width: 1100px) {
  .summary-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .node-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .span-2 {
    grid-column: span 1;
  }

  .filter-keyword {
    width: 100%;
  }
}
</style>
