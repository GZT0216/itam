import axios, { AxiosError, type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

import type { ApiEnvelope, TokenBundle } from '@/types/api'
import {
  clearTokenBundle,
  getAccessToken,
  getRefreshToken,
  saveTokenBundle,
} from '@/utils/token'

const API_BASE = (import.meta.env.VITE_API_BASE || '/api/v1').replace(/\/$/, '')

export const TODO_REFRESH_EVENT = 'itam:todo-refresh'

function notifyTodoRefresh(config?: InternalAxiosRequestConfig): void {
  const method = (config?.method || 'get').toLowerCase()
  if (method === 'get' || method === 'head' || method === 'options') return
  const url = config?.url ?? ''
  if (url.includes('/auth/') || url.includes('/todos')) return
  window.dispatchEvent(new CustomEvent(TODO_REFRESH_EVENT))
}

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

const service = axios.create({
  baseURL: API_BASE,
  timeout: 20000,
  headers: { 'Content-Type': 'application/json' },
})

service.interceptors.request.use((config) => {
  const accessToken = getAccessToken()
  if (accessToken) {
    config.headers.set('Authorization', `Bearer ${accessToken}`)
  }
  return config
})

let refreshPromise: Promise<string> | null = null

async function refreshAccessToken(): Promise<string> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        throw new Error('没有可用的刷新令牌')
      }
      const response = await axios.post<ApiEnvelope<TokenBundle>>(
        `${API_BASE}/auth/refresh`,
        { refresh_token: refreshToken },
        { timeout: 15000 },
      )
      if (response.data.code !== 0 || !response.data.data) {
        throw new Error(response.data.message || '登录状态已失效')
      }
      saveTokenBundle(response.data.data)
      return response.data.data.access_token
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

function redirectToLogin(): void {
  clearTokenBundle()
  if (window.location.pathname === '/login') return
  const redirect = encodeURIComponent(
    window.location.pathname + window.location.search + window.location.hash,
  )
  window.location.replace(`/login?redirect=${redirect}`)
}

service.interceptors.response.use(
  (response) => {
    const envelope = response.data as ApiEnvelope<unknown>
    if (envelope && typeof envelope.code === 'number') {
      if (envelope.code === 0) {
        notifyTodoRefresh(response.config)
        return envelope.data
      }
      ElMessage.error(envelope.message || '请求失败')
      return Promise.reject(new Error(envelope.message || '请求失败'))
    }
    notifyTodoRefresh(response.config)
    return response.data
  },
  async (error: AxiosError<ApiEnvelope<unknown>>) => {
    const status = error.response?.status
    const envelope = error.response?.data
    const config = error.config as RetryableConfig | undefined
    const requestUrl = config?.url ?? ''
    const isAuthRequest =
      requestUrl.includes('/auth/login') || requestUrl.includes('/auth/refresh')

    if (status === 401 && !isAuthRequest && config && !config._retry) {
      config._retry = true
      try {
        const accessToken = await refreshAccessToken()
        config.headers.set('Authorization', `Bearer ${accessToken}`)
        return service(config)
      } catch {
        ElMessage.error('登录已过期，请重新登录')
        redirectToLogin()
        return Promise.reject(error)
      }
    }

    if (status === 401 && !isAuthRequest) {
      redirectToLogin()
    }

    if (status === 403 && envelope?.code === 40310) {
      ElMessage.warning(envelope.message || '请先修改初始密码')
      if (window.location.pathname !== '/change-password') {
        window.location.assign('/change-password')
      }
      return Promise.reject(error)
    }

    const message = envelope?.message
    if (message) {
      ElMessage.error(message)
    } else if (!error.response) {
      ElMessage.error('无法连接服务器，请检查网络或后端服务状态')
    } else if (status && status >= 500) {
      ElMessage.error('服务器开小差了，请稍后重试')
    }

    return Promise.reject(error)
  },
)

export function request<T>(config: AxiosRequestConfig): Promise<T> {
  return service.request(config) as unknown as Promise<T>
}

export { API_BASE }
