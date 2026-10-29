<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Box, Camera, Refresh, Tickets } from '@element-plus/icons-vue'

import RequestDetailDrawer from '@/components/asset-flow/RequestDetailDrawer.vue'
import ScanDialog from '@/components/ScanDialog.vue'
import { assetFlowApi } from '@/api/assetFlow'
import type {
  AssetHistoryItem,
  AssetRequestItem,
  AvailableAsset,
  MyAssetItem,
} from '@/types/assetFlow'
import { ASSET_STATUS_TAG_TYPES } from '@/types/asset'
import { formatDateTime } from '@/utils/format'

const loading = ref(false)
const assets = ref<MyAssetItem[]>([])
const historyVisible = ref(false)
const historyLoading = ref(false)
const historyAsset = ref<MyAssetItem | null>(null)
const historyItems = ref<AssetHistoryItem[]>([])

const returnVisible = ref(false)
const returnAsset = ref<MyAssetItem | null>(null)
const returnReason = ref('')
const returnSubmitting = ref(false)
const returnVerified = ref(false)
const returnScanVisible = ref(false)

const requestVisible = ref(false)
const requestDetail = ref<AssetRequestItem | null>(null)

const scanVisible = ref(false)

const stats = computed(() => {
  const borrowed = assets.value.filter((item) => item.status === 'BORROWED').length
  const dueSoon = assets.value.filter(
    (item) =>
      item.days_to_due !== null && item.days_to_due >= 0 && item.days_to_due <= 3,
  ).length
  const overdue = assets.value.filter((item) => item.is_overdue).length
  return { total: assets.value.length, borrowed, dueSoon, overdue }
})

async function fetchAssets(): Promise<void> {
  loading.value = true
  try {
    assets.value = await assetFlowApi.myAssets()
  } finally {
    loading.value = false
  }
}

async function openHistory(item: MyAssetItem): Promise<void> {
  historyAsset.value = item
  historyVisible.value = true
  historyLoading.value = true
  historyItems.value = []
  try {
    historyItems.value = await assetFlowApi.assetHistory(item.asset_id)
  } finally {
    historyLoading.value = false
  }
}

function openReturn(item: MyAssetItem): void {
  returnAsset.value = item
  returnReason.value = ''
  returnVerified.value = false
  returnVisible.value = true
}

async function submitReturn(): Promise<void> {
  if (!returnAsset.value) return
  returnSubmitting.value = true
  try {
    const created = await assetFlowApi.createReturn({
      asset_id: returnAsset.value.asset_id,
      reason: returnReason.value || null,
    })
    ElMessage.success(`${created.request_no} 已提交，请等待资产管理员确认归还`)
    returnVisible.value = false
    await fetchAssets()
  } finally {
    returnSubmitting.value = false
  }
}

function verifyReturnScan(asset: AvailableAsset): void {
  if (!returnAsset.value) return
  if (asset.id !== returnAsset.value.asset_id) {
    returnVerified.value = false
    ElMessage.error(`扫码资产与待归还资产不一致：${asset.asset_no}`)
    return
  }
  returnVerified.value = true
  ElMessage.success(`扫码核对通过：${asset.asset_no} ${asset.name}`)
}

async function openRequest(row: MyAssetItem): Promise<void> {
  const id = row.return_request_id ?? row.request_id
  if (!id) {
    ElMessage.info('该资产暂无关联业务单据')
    return
  }
  requestDetail.value = await assetFlowApi.getRequest(id)
  requestVisible.value = true
}

function dueText(item: MyAssetItem): string {
  if (!item.expected_return_date) return ''
  if (item.days_to_due === null) return item.expected_return_date
  if (item.days_to_due < 0) return `已逾期 ${Math.abs(item.days_to_due)} 天`
  if (item.days_to_due === 0) return '今天到期'
  return `${item.expected_return_date} 到期 · 剩 ${item.days_to_due} 天`
}

function handleScan(
  asset: AvailableAsset,
  result: { requests: AssetRequestItem[] },
): void {
  const match = assets.value.find((item) => item.asset_id === asset.id)
  if (match) {
    void openHistory(match)
    return
  }
  if (result.requests.length) {
    void assetFlowApi.getRequest(result.requests[0].id).then((detail) => {
      requestDetail.value = detail
      requestVisible.value = true
    })
    return
  }
  ElMessage.info('该资产不在你名下')
}

onMounted(fetchAssets)
</script>

<template>
  <div class="page mine-page">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">MY ASSETS</p>
        <h1 class="page-title">我的资产</h1>
        <p class="page-subtitle">
          查看当前由你保管的资产、借用到期时间与历次状态变更记录，并可直接发起归还。
        </p>
      </div>
      <div class="page-actions">
        <el-button :icon="Camera" @click="scanVisible = true">扫码查询</el-button>
        <el-button :icon="Refresh" :loading="loading" @click="fetchAssets">刷新</el-button>
      </div>
    </header>

    <section class="stats-strip">
      <div class="stat-card surface-card">
        <span>名下资产</span>
        <strong>{{ stats.total }}</strong>
      </div>
      <div class="stat-card surface-card">
        <span>借用中</span>
        <strong>{{ stats.borrowed }}</strong>
      </div>
      <div class="stat-card surface-card warning">
        <span>3 天内到期</span>
        <strong>{{ stats.dueSoon }}</strong>
      </div>
      <div class="stat-card surface-card danger">
        <span>已逾期</span>
        <strong>{{ stats.overdue }}</strong>
      </div>
    </section>

    <div v-loading="loading" class="asset-grid">
      <article
        v-for="item in assets"
        :key="item.asset_id"
        class="asset-card surface-card hover-lift"
        :class="{ overdue: item.is_overdue }"
      >
        <header class="asset-card-head">
          <span class="asset-icon"><el-icon><Box /></el-icon></span>
          <div class="asset-title">
            <h3>{{ item.name }}</h3>
            <p>{{ item.asset_no }}</p>
          </div>
          <el-tag :type="ASSET_STATUS_TAG_TYPES[item.status]" effect="light">
            {{ item.status_label }}
          </el-tag>
        </header>

        <div class="asset-meta">
          <span>{{ item.category_name || '未分类' }}</span>
          <span>{{ item.model_name || '未指定型号' }}</span>
          <span>{{ item.location || '未填写位置' }}</span>
        </div>

        <div v-if="item.expected_return_date" class="due-banner" :class="{ danger: item.is_overdue }">
          <span>{{ dueText(item) }}</span>
          <el-tag v-if="item.is_overdue" type="danger" size="small" effect="light">逾期</el-tag>
          <el-tag
            v-else-if="item.days_to_due !== null && item.days_to_due <= 3"
            type="warning"
            size="small"
            effect="light"
          >
            即将到期
          </el-tag>
        </div>

        <div v-if="item.return_pending" class="return-pending">
          <el-tag type="warning" effect="light">归还单待管理员确认</el-tag>
        </div>

        <footer class="asset-card-actions">
          <el-button link type="primary" @click="openHistory(item)">状态记录</el-button>
          <el-button
            v-if="item.request_id || item.return_request_id"
            link
            type="info"
            @click="openRequest(item)"
          >
            查看单据
          </el-button>
          <el-button
            v-if="!item.return_pending"
            type="warning"
            plain
            size="small"
            @click="openReturn(item)"
          >
            发起归还
          </el-button>
        </footer>
      </article>

      <div v-if="!loading && !assets.length" class="empty-state surface-card">
        <el-icon :size="34"><Tickets /></el-icon>
        <p>当前没有登记在你名下的资产</p>
        <small>如需领用，请前往「领用申请」提交申请，审批出库后资产会自动出现在这里。</small>
      </div>
    </div>

    <el-drawer v-model="historyVisible" size="560px">
      <template #header>
        <div v-if="historyAsset" class="drawer-head">
          <div>
            <p class="drawer-eyebrow">ASSET HISTORY</p>
            <h3>{{ historyAsset.name }}</h3>
            <p class="drawer-sub">{{ historyAsset.asset_no }}</p>
          </div>
          <el-tag :type="ASSET_STATUS_TAG_TYPES[historyAsset.status]" effect="light">
            {{ historyAsset.status_label }}
          </el-tag>
        </div>
      </template>

      <template v-if="historyAsset">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="分类">
            {{ historyAsset.category_name || '未分类' }}
          </el-descriptions-item>
          <el-descriptions-item label="型号">
            {{ historyAsset.model_name || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="存放位置">
            {{ historyAsset.location || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="所属部门">
            {{ historyAsset.dept_name || '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="借用时间">
            {{ formatDateTime(historyAsset.borrowed_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="预计归还">
            {{ historyAsset.expected_return_date || '—' }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <p class="detail-section-title">状态变更记录</p>
          <div v-loading="historyLoading">
            <el-timeline v-if="historyItems.length">
              <el-timeline-item
                v-for="record in historyItems"
                :key="record.id"
                :timestamp="formatDateTime(record.created_at)"
                :type="record.to_status === 'IN_STOCK' ? 'success' : 'primary'"
                placement="top"
              >
                <div class="history-title">{{ record.action_label }}</div>
                <div class="history-status">
                  <el-tag size="small" effect="plain">{{ record.from_status_label }}</el-tag>
                  <span>→</span>
                  <el-tag size="small" type="success" effect="light">
                    {{ record.to_status_label }}
                  </el-tag>
                </div>
                <p class="history-summary">{{ record.summary || '—' }}</p>
                <p class="history-meta">
                  责任人：{{ record.before_snapshot.custodian_name || '无' }}
                  →
                  {{ record.after_snapshot.custodian_name || '无' }}
                  <span>·</span>
                  操作人：{{ record.operator_name || '系统' }}
                </p>
              </el-timeline-item>
            </el-timeline>
            <p v-else-if="!historyLoading" class="empty-tip">暂无状态变更记录</p>
          </div>
        </div>

        <div class="drawer-actions">
          <el-button
            v-if="!historyAsset.return_pending"
            type="warning"
            @click="openReturn(historyAsset)"
          >
            发起归还
          </el-button>
        </div>
      </template>
    </el-drawer>

    <el-dialog v-model="returnVisible" title="发起资产归还" width="520px">
      <div v-if="returnAsset" class="return-summary">
        <div>
          <span>{{ returnAsset.name }}</span>
          <small>{{ returnAsset.asset_no }} · {{ returnAsset.location || '未填写位置' }}</small>
        </div>
        <el-tag :type="ASSET_STATUS_TAG_TYPES[returnAsset.status]" effect="light">
          {{ returnAsset.status_label }}
        </el-tag>
      </div>

      <div class="scan-verify">
        <el-button :icon="Camera" @click="returnScanVisible = true">扫码核对资产</el-button>
        <el-tag v-if="returnVerified" type="success" effect="light">扫码核对通过</el-tag>
        <span v-else>建议扫码核对实物编号后再提交</span>
      </div>

      <el-form label-position="top">
        <el-form-item label="归还原因（选填）">
          <el-input
            v-model="returnReason"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="例如：岗位调整、设备更换、借用到期"
          />
        </el-form-item>
      </el-form>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="提交后资产进入「待归还确认」，管理员确认后恢复在库状态并清空责任人"
      />

      <template #footer>
        <el-button @click="returnVisible = false">取消</el-button>
        <el-button type="warning" :loading="returnSubmitting" @click="submitReturn">
          提交归还申请
        </el-button>
      </template>
    </el-dialog>

    <RequestDetailDrawer v-model="requestVisible" :request="requestDetail" />
    <ScanDialog
      v-model="returnScanVisible"
      title="扫码核对归还资产"
      hint="扫描或输入实物编号，系统会校验是否与当前归还资产一致。"
      @select="verifyReturnScan"
    />
    <ScanDialog v-model="scanVisible" @select="handleScan" />
  </div>
</template>

<style scoped>
.page-actions {
  display: flex;
  gap: 10px;
}

.stats-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.stat-card {
  padding: 16px 18px;
}

.stat-card span {
  color: var(--text-3);
  font-size: 12px;
}

.stat-card strong {
  display: block;
  margin-top: 6px;
  font-family: var(--font-number);
  font-size: 26px;
  color: var(--text-1);
}

.stat-card.warning strong {
  color: var(--warning);
}

.stat-card.danger strong {
  color: var(--danger);
}

.asset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  min-height: 180px;
}

.asset-card {
  display: flex;
  flex-direction: column;
  padding: 18px;
  gap: 14px;
}

.asset-card.overdue {
  border-color: rgba(239, 68, 68, 0.45);
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.08);
}

.asset-card-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.asset-icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 12px;
  background: var(--gradient-brand-soft);
  color: var(--brand);
  font-size: 18px;
}

.asset-title {
  flex: 1;
  min-width: 0;
}

.asset-title h3 {
  font-size: 15px;
  font-weight: 650;
  color: var(--text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.asset-title p {
  margin-top: 2px;
  color: var(--text-3);
  font-size: 11.5px;
  font-family: var(--font-number);
}

.asset-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--text-2);
  font-size: 12px;
}

.asset-meta span {
  padding: 3px 8px;
  border-radius: 7px;
  background: var(--surface-muted);
}

.due-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 10px;
  background: rgba(245, 158, 11, 0.1);
  color: #b45309;
  font-size: 12.5px;
}

.due-banner.danger {
  background: rgba(239, 68, 68, 0.1);
  color: var(--danger);
}

.return-pending {
  padding: 8px 0;
}

.asset-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: auto;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.asset-card-actions .el-button:last-child {
  margin-left: auto;
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 60px 20px;
  color: var(--text-3);
  text-align: center;
}

.empty-state p {
  color: var(--text-2);
  font-weight: 600;
}

.empty-state small {
  max-width: 420px;
  line-height: 1.8;
}

.drawer-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.drawer-head h3 {
  font-size: 17px;
  font-weight: 700;
}

.drawer-eyebrow {
  color: var(--brand);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.14em;
}

.drawer-sub {
  margin-top: 2px;
  color: var(--text-3);
  font-size: 12px;
  font-family: var(--font-number);
}

.detail-section {
  margin-top: 20px;
}

.detail-section-title {
  margin-bottom: 12px;
  color: var(--text-2);
  font-size: 12.5px;
  font-weight: 650;
}

.history-title {
  font-weight: 650;
  color: var(--text-1);
}

.history-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  color: var(--text-3);
  font-size: 12px;
}

.history-summary {
  margin-top: 6px;
  color: var(--text-2);
  font-size: 12.5px;
}

.history-meta {
  margin-top: 4px;
  color: var(--text-3);
  font-size: 11.5px;
}

.history-meta span {
  margin: 0 4px;
}

.empty-tip {
  color: var(--text-3);
  font-size: 12.5px;
  padding: 12px 0;
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.return-summary {
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

.return-summary span {
  display: block;
  font-weight: 650;
}

.return-summary small {
  display: block;
  margin-top: 2px;
  color: var(--text-3);
  font-size: 12px;
}

.scan-verify {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  color: var(--text-3);
  font-size: 12px;
}

@media (max-width: 1100px) {
  .stats-strip {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
