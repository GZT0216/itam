<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import {
  ArrowRight,
  CircleCheck,
  Connection,
  DataLine,
  Key,
  Lock,
  Monitor,
  User,
} from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'
import type { LoginPayload } from '@/types/api'

const REMEMBER_KEY = 'itam_remember_username'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const formRef = ref<FormInstance>()
const loading = ref(false)
const remember = ref(true)
const form = reactive<LoginPayload>({ username: '', password: '' })
const year = new Date().getFullYear()

const rules: FormRules<LoginPayload> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

onMounted(() => {
  const saved = localStorage.getItem(REMEMBER_KEY)
  if (saved) {
    form.username = saved
    remember.value = true
  }
})

function redirectTarget(): string {
  const value = route.query.redirect
  const target = (typeof value === 'string' ? value : '/dashboard').split('#')[0]
  if (!target.startsWith('/') || target.startsWith('//')) return '/dashboard'
  const resolved = router.resolve(target)
  return resolved.matched.length ? resolved.fullPath : '/dashboard'
}

async function handleSubmit(): Promise<void> {
  if (!formRef.value || loading.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    const username = form.username.trim()
    const result = await auth.login({ username, password: form.password })
    if (remember.value) {
      localStorage.setItem(REMEMBER_KEY, username)
    } else {
      localStorage.removeItem(REMEMBER_KEY)
    }
    ElMessage.success(`欢迎回来，${result.user.real_name}`)
    const destination = result.must_change_password ? '/change-password' : redirectTarget()
    await router.replace(destination)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-screen">
    <div class="login-grid" aria-hidden="true" />
    <div class="orb orb-a" aria-hidden="true" />
    <div class="orb orb-b" aria-hidden="true" />

    <section class="login-showcase">
      <div class="showcase-brand">
        <div class="brand-mark">IT</div>
        <div class="brand-copy">
          <span class="brand-name">ITAM</span>
          <span class="brand-sub">IT ASSET CONTROL</span>
        </div>
      </div>

      <div class="showcase-body">
        <p class="showcase-eyebrow">IT ASSET MANAGEMENT SYSTEM</p>
        <h1 class="showcase-title">
          把每一份 IT 资产<br />
          变成<span class="gradient-text">清晰的数字资产</span>
        </h1>
        <p class="showcase-lead">
          从采购入库、领用调拨到维修报废，每一次流转都由后端状态机驱动，
          让资产、责任人与审计记录始终一致。
        </p>

        <ul class="feature-list">
          <li>
            <span class="feature-icon"><DataLine /></span>
            <div>
              <strong>全生命周期闭环</strong>
              <p>入库 → 领用 → 调拨 → 维修 → 报废，历史永不物理删除</p>
            </div>
          </li>
          <li>
            <span class="feature-icon"><Key /></span>
            <div>
              <strong>四级权限控制</strong>
              <p>菜单、操作、数据、字段四层校验，前后端双重过滤</p>
            </div>
          </li>
          <li>
            <span class="feature-icon"><Connection /></span>
            <div>
              <strong>事务与乐观锁</strong>
              <p>关键操作使用数据库事务，并发领用与调拨不产生重复分配</p>
            </div>
          </li>
        </ul>
      </div>

      <div class="showcase-footer">
        <div class="phase-pill">
          <span class="status-dot" />
          Phase 1 · 核心资产管理已上线
        </div>
        <div class="showcase-meta">
          <span><Monitor /> Web 控制台</span>
          <span><CircleCheck /> 审计可追溯</span>
        </div>
      </div>
    </section>

    <section class="login-panel">
      <div class="login-card">
        <div class="mobile-brand">
          <div class="brand-mark">IT</div>
          <div>
            <span class="brand-name">ITAM</span>
            <span class="brand-sub">IT ASSET CONTROL</span>
          </div>
        </div>

        <p class="card-eyebrow">SIGN IN</p>
        <h2 class="card-title">登录控制台</h2>
        <p class="card-subtitle">使用本地账号或域账号（AD / LDAP）登录</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          size="large"
          class="login-form"
          @submit.prevent="handleSubmit"
        >
          <el-form-item prop="username">
            <el-input
              v-model="form.username"
              :prefix-icon="User"
              placeholder="用户名"
              autocomplete="username"
              clearable
            />
          </el-form-item>
          <el-form-item prop="password">
            <el-input
              v-model="form.password"
              :prefix-icon="Lock"
              type="password"
              placeholder="密码"
              autocomplete="current-password"
              show-password
              @keyup.enter="handleSubmit"
            />
          </el-form-item>

          <div class="login-options">
            <el-checkbox v-model="remember">记住用户名</el-checkbox>
            <span class="forgot-hint">本地账号请联系管理员 · 域账号请在 AD 中重置</span>
          </div>

          <el-button class="login-submit" type="primary" :loading="loading" @click="handleSubmit">
            <span>{{ loading ? '正在验证身份' : '进入控制台' }}</span>
            <el-icon v-if="!loading" class="submit-arrow"><ArrowRight /></el-icon>
          </el-button>
        </el-form>

        <div class="security-note">
          <el-icon><Lock /></el-icon>
          <span>JWT 双令牌认证 · 登录与敏感操作均记录审计日志</span>
        </div>
      </div>

      <footer class="login-footer">ITAM · IT 资产管理系统 <span>v0.1.0</span> · © {{ year }}</footer>
    </section>
  </div>
</template>

<style scoped>
.login-screen {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1.06fr) minmax(440px, 0.94fr);
  min-height: 100vh;
  overflow: hidden;
  background: #070f1d;
}

.login-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 178, 224, 0.055) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 178, 224, 0.055) 1px, transparent 1px);
  background-size: 54px 54px;
  mask-image: radial-gradient(ellipse 70% 70% at 30% 40%, #000 25%, transparent 78%);
  pointer-events: none;
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
  animation: float 16s ease-in-out infinite;
}

.orb-a {
  width: 460px;
  height: 460px;
  top: -160px;
  left: -80px;
  background: rgba(37, 99, 235, 0.32);
}

.orb-b {
  width: 420px;
  height: 420px;
  bottom: -160px;
  left: 34%;
  background: rgba(6, 182, 212, 0.16);
  animation-delay: -7s;
}

@keyframes float {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(18px, -22px, 0) scale(1.06);
  }
}

.login-showcase {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 36px;
  padding: 48px 64px 42px;
  color: #eaf1fc;
}

.showcase-brand,
.mobile-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-mark {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border-radius: 13px;
  background: var(--gradient-brand);
  color: #fff;
  font-family: var(--font-number);
  font-size: 16px;
  font-weight: 800;
  letter-spacing: -0.06em;
  box-shadow: 0 14px 32px -12px rgba(37, 99, 235, 0.9);
}

.brand-copy,
.mobile-brand > div:last-child {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-name {
  color: #f5f8ff;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.brand-sub {
  margin-top: 3px;
  color: #6f83a0;
  font-size: 10px;
  letter-spacing: 0.18em;
}

.showcase-body {
  max-width: 580px;
  margin-top: -24px;
}

.showcase-eyebrow {
  color: #6ea8ff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.24em;
}

.showcase-title {
  margin: 16px 0 18px;
  color: #f6f9ff;
  font-size: clamp(36px, 4vw, 50px);
  font-weight: 750;
  line-height: 1.16;
  letter-spacing: -0.035em;
}

.showcase-title .gradient-text {
  background: linear-gradient(100deg, #68a4ff 0%, #3dd6f5 70%, #7ef0e1 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.showcase-lead {
  max-width: 500px;
  color: #8ba0bd;
  font-size: 14.5px;
  line-height: 1.8;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
  margin: 34px 0 0;
  padding: 0;
  list-style: none;
}

.feature-list li {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.feature-icon {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border: 1px solid rgba(138, 173, 226, 0.16);
  border-radius: 12px;
  background: rgba(120, 160, 220, 0.08);
  color: #7db4ff;
}

.feature-icon svg {
  width: 18px;
  height: 18px;
}

.feature-list strong {
  display: block;
  color: #dce8f9;
  font-size: 13.5px;
  font-weight: 600;
}

.feature-list p {
  margin-top: 4px;
  color: #778ca9;
  font-size: 12.5px;
  line-height: 1.65;
}

.showcase-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  flex-wrap: wrap;
}

.phase-pill {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 8px 14px;
  border: 1px solid rgba(138, 173, 226, 0.14);
  border-radius: 999px;
  background: rgba(120, 160, 220, 0.07);
  color: #98abc6;
  font-size: 11.5px;
  white-space: nowrap;
}

.phase-pill .status-dot {
  background: #34d399;
}

.showcase-meta {
  display: flex;
  gap: 18px;
  color: #61758f;
  font-size: 11.5px;
}

.showcase-meta span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.showcase-meta svg {
  width: 14px;
  height: 14px;
}

.login-panel {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 22px;
  padding: 42px 40px 26px;
  background:
    radial-gradient(680px 360px at 80% 0%, rgba(6, 182, 212, 0.08), transparent 60%),
    radial-gradient(720px 400px at 10% 100%, rgba(37, 99, 235, 0.07), transparent 62%),
    var(--page-bg);
}

.login-card {
  width: 100%;
  max-width: 424px;
  padding: 38px 36px 32px;
  border: 1px solid var(--border);
  border-radius: 26px;
  background: var(--surface);
  box-shadow: 0 34px 90px -46px rgba(15, 23, 42, 0.55);
}

.mobile-brand {
  display: none;
  margin-bottom: 26px;
}

.card-eyebrow {
  color: var(--brand);
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.22em;
}

.card-title {
  margin: 8px 0 6px;
  color: var(--text-1);
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
}

.card-subtitle {
  color: var(--text-2);
  font-size: 13px;
}

.login-form {
  margin-top: 28px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.login-form :deep(.el-input__wrapper) {
  height: 48px;
  padding: 0 14px;
  border-radius: 12px;
  background: var(--surface-muted);
  box-shadow: 0 0 0 1px var(--border) inset;
}

.login-form :deep(.el-input__wrapper.is-focus) {
  background: var(--surface);
}

.login-form :deep(.el-input__inner) {
  font-size: 13.5px;
}

.login-form :deep(.el-input__prefix) {
  color: var(--text-3);
  margin-right: 4px;
}

.login-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin: 2px 0 22px;
}

.login-options :deep(.el-checkbox__label) {
  color: var(--text-2);
  font-size: 12.5px;
}

.forgot-hint {
  color: var(--text-3);
  font-size: 12px;
}

.login-submit {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 12px;
  background: var(--gradient-brand);
  font-size: 14px;
  font-weight: 600;
  letter-spacing: 0.02em;
  box-shadow: 0 18px 34px -18px rgba(37, 99, 235, 0.95);
}

.login-submit:hover,
.login-submit:focus {
  background: linear-gradient(120deg, #1d4ed8 0%, #0284c7 55%, #0891b2 100%);
}

.login-submit :deep(span) {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.submit-arrow {
  font-size: 15px;
  transition: transform 0.2s ease;
}

.login-submit:hover .submit-arrow {
  transform: translateX(3px);
}

.security-note {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px dashed var(--border);
  color: var(--text-3);
  font-size: 11.5px;
  text-align: center;
}

.security-note .el-icon {
  font-size: 13px;
}

.login-footer {
  color: var(--text-3);
  font-size: 11px;
  text-align: center;
}

.login-footer span {
  color: var(--text-2);
  font-weight: 600;
}

@media (max-width: 1024px) {
  .login-screen {
    grid-template-columns: 1fr;
  }

  .login-showcase {
    display: none;
  }

  .login-panel {
    padding: 32px 20px 24px;
  }

  .mobile-brand {
    display: flex;
  }

  .mobile-brand .brand-name {
    color: var(--text-1);
  }
}

@media (max-width: 480px) {
  .login-card {
    padding: 30px 22px 26px;
    border-radius: 22px;
  }

  .login-options {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .orb {
    animation: none;
  }

  .submit-arrow {
    transition: none;
  }
}
</style>
