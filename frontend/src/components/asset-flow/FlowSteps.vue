<script setup lang="ts">
import { computed } from 'vue'

import { flowActive, flowSteps, isFlowInterrupted } from '@/types/assetFlow'
import type { AssetRequestStatus, AssetRequestType } from '@/types/assetFlow'

const props = defineProps<{
  requestType: AssetRequestType
  status: AssetRequestStatus
}>()

const steps = computed(() => flowSteps(props.requestType))
const active = computed(() => flowActive(props.requestType, props.status))
const interrupted = computed(() => isFlowInterrupted(props.status))
const interruptedText = computed(() =>
  props.status === 'REJECTED' ? '审批未通过，流程结束' : '申请已撤销，流程结束',
)
</script>

<template>
  <div class="flow-steps">
    <el-steps
      :active="active"
      :process-status="interrupted ? 'error' : 'process'"
      finish-status="success"
      align-center
    >
      <el-step v-for="label in steps" :key="label" :title="label" />
    </el-steps>
    <div v-if="interrupted" class="flow-interrupted">
      <el-tag type="danger" effect="light">{{ interruptedText }}</el-tag>
    </div>
  </div>
</template>

<style scoped>
.flow-steps {
  padding: 18px 6px 10px;
  border-radius: 14px;
  background: var(--surface-muted);
  border: 1px solid var(--border);
}

.flow-steps :deep(.el-step__title) {
  font-size: 12.5px;
}

.flow-interrupted {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}
</style>
