<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, VideoCamera } from '@element-plus/icons-vue'

import { assetFlowApi } from '@/api/assetFlow'
import type { AvailableAsset, ScanAssetResult } from '@/types/assetFlow'

const props = defineProps<{
  modelValue: boolean
  title?: string
  hint?: string
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
  (event: 'select', asset: AvailableAsset, result: ScanAssetResult): void
}>()

const code = ref('')
const loading = ref(false)
const result = ref<ScanAssetResult | null>(null)
const cameraOpen = ref(false)
const cameraStarting = ref(false)
const videoRef = ref<HTMLVideoElement>()
let stream: MediaStream | null = null
let scanTimer: number | undefined

const cameraSupported = computed(
  () =>
    typeof window !== 'undefined' &&
    'BarcodeDetector' in window &&
    Boolean(navigator.mediaDevices?.getUserMedia) &&
    window.isSecureContext,
)

function close(): void {
  emit('update:modelValue', false)
}

async function search(): Promise<void> {
  const keyword = code.value.trim()
  if (!keyword) {
    ElMessage.warning('请输入或扫描资产编号 / 序列号')
    return
  }
  loading.value = true
  try {
    result.value = await assetFlowApi.scan(keyword)
  } finally {
    loading.value = false
  }
}

function choose(): void {
  if (!result.value) return
  emit('select', result.value.asset, result.value)
  close()
}

async function startCamera(): Promise<void> {
  if (!cameraSupported.value) {
    ElMessage.warning('当前环境不支持摄像头扫码，请使用扫码枪或手动输入编号')
    return
  }
  cameraStarting.value = true
  try {
    const media = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment' },
    })
    stream = media
    cameraOpen.value = true
    await nextTick()
    if (!videoRef.value) return
    videoRef.value.srcObject = media
    await videoRef.value.play()
    const Detector = (window as unknown as { BarcodeDetector: new (options: { formats: string[] }) => { detect: (source: HTMLVideoElement) => Promise<Array<{ rawValue: string }>> } }).BarcodeDetector
    const detector = new Detector({
      formats: ['qr_code', 'code_128', 'code_39', 'ean_13'],
    })
    scanTimer = window.setInterval(async () => {
      if (!videoRef.value || videoRef.value.readyState < 2) return
      try {
        const codes = await detector.detect(videoRef.value)
        if (codes.length && codes[0]?.rawValue) {
          code.value = codes[0].rawValue
          stopCamera()
          await search()
        }
      } catch {
        // 单帧识别失败不影响继续扫描
      }
    }, 500)
  } catch {
    ElMessage.warning('无法启动摄像头，请确认已授权且通过 HTTPS / localhost 访问')
    stopCamera()
  } finally {
    cameraStarting.value = false
  }
}

function stopCamera(): void {
  if (scanTimer) {
    window.clearInterval(scanTimer)
    scanTimer = undefined
  }
  if (stream) {
    stream.getTracks().forEach((track) => track.stop())
    stream = null
  }
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  cameraOpen.value = false
}

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) {
      stopCamera()
      return
    }
    code.value = ''
    result.value = null
  },
)

onBeforeUnmount(stopCamera)
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    :title="title || '扫码 / 编号查询'"
    width="540px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
    @closed="stopCamera"
  >
    <p class="scan-hint">
      {{ hint || '支持 USB 扫码枪直接输入，或手动填写资产编号 / 序列号后查询。' }}
    </p>

    <div class="scan-input">
      <el-input
        v-model="code"
        size="large"
        placeholder="资产编号或序列号，例如 ITAM-2026-0001"
        clearable
        autofocus
        @keyup.enter="search"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" size="large" :loading="loading" @click="search">
        查询
      </el-button>
      <el-button
        size="large"
        :icon="VideoCamera"
        :loading="cameraStarting"
        @click="startCamera"
      >
        摄像头
      </el-button>
    </div>

    <div v-if="cameraOpen" class="scan-camera">
      <video ref="videoRef" muted playsinline />
      <span>将二维码 / 条形码对准摄像头</span>
    </div>

    <div v-if="result" class="scan-result">
      <div class="scan-asset">
        <div>
          <span class="scan-asset-name">{{ result.asset.name }}</span>
          <span class="scan-asset-no">{{ result.asset.asset_no }}</span>
        </div>
        <el-tag :type="result.asset.status === 'IN_STOCK' ? 'success' : 'info'" effect="light">
          {{ result.asset.status_label }}
        </el-tag>
      </div>
      <div class="scan-meta">
        <span>{{ result.asset.category_name || '未分类' }}</span>
        <span>{{ result.asset.model_name || '未指定型号' }}</span>
        <span>{{ result.asset.location || '未填写位置' }}</span>
      </div>
      <div v-if="result.requests.length" class="scan-requests">
        <p class="scan-requests-title">进行中的业务单据</p>
        <div
          v-for="request in result.requests"
          :key="request.id"
          class="scan-request-row"
        >
          <span>{{ request.request_no }}</span>
          <span>{{ request.request_type_label }} · {{ request.applicant_name }}</span>
          <el-tag size="small" :type="request.status_tag_type" effect="light">
            {{ request.status_label }}
          </el-tag>
        </div>
      </div>
      <div class="scan-actions">
        <el-button type="primary" @click="choose">选用该资产</el-button>
      </div>
    </div>

    <p v-else class="scan-tip">
      扫码枪扫描后会自动填入编号；生产环境使用 HTTP 访问时，浏览器摄像头不可用，请以扫码枪或手动输入为主。
    </p>
  </el-dialog>
</template>

<style scoped>
.scan-hint {
  color: var(--text-2);
  font-size: 13px;
  margin-bottom: 14px;
}

.scan-input {
  display: flex;
  gap: 10px;
  align-items: center;
}

.scan-input .el-input {
  flex: 1;
}

.scan-camera {
  position: relative;
  margin-top: 14px;
  border-radius: 14px;
  overflow: hidden;
  background: #07101d;
  aspect-ratio: 16 / 9;
}

.scan-camera video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.scan-camera span {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 10px;
  text-align: center;
  color: #dbe7f8;
  font-size: 12px;
}

.scan-result {
  margin-top: 16px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: var(--surface-muted);
}

.scan-asset {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.scan-asset-name {
  display: block;
  font-weight: 650;
  color: var(--text-1);
}

.scan-asset-no {
  display: block;
  margin-top: 2px;
  color: var(--text-3);
  font-size: 12px;
  font-family: var(--font-number);
}

.scan-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  color: var(--text-2);
  font-size: 12.5px;
}

.scan-requests {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed var(--border);
}

.scan-requests-title {
  color: var(--text-3);
  font-size: 11.5px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 8px;
}

.scan-request-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  font-size: 12.5px;
  color: var(--text-2);
}

.scan-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

.scan-tip {
  margin-top: 16px;
  color: var(--text-3);
  font-size: 12px;
  line-height: 1.7;
}
</style>
