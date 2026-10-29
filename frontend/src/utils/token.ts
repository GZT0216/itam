import type { TokenBundle } from '@/types/api'

const ACCESS_TOKEN_KEY = 'itam_access_token'
const REFRESH_TOKEN_KEY = 'itam_refresh_token'

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function saveTokenBundle(bundle: Pick<TokenBundle, 'access_token' | 'refresh_token'>): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, bundle.access_token)
  localStorage.setItem(REFRESH_TOKEN_KEY, bundle.refresh_token)
}

export function clearTokenBundle(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}
