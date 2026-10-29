import { request } from '@/api/request'
import type {
  ChangePasswordPayload,
  CurrentUser,
  LoginPayload,
  LoginResult,
  TokenBundle,
} from '@/types/api'

export const authApi = {
  login(payload: LoginPayload): Promise<LoginResult> {
    return request<LoginResult>({
      url: '/auth/login',
      method: 'post',
      data: payload,
    })
  },

  refresh(refreshToken: string): Promise<TokenBundle> {
    return request<TokenBundle>({
      url: '/auth/refresh',
      method: 'post',
      data: { refresh_token: refreshToken },
    })
  },

  logout(refreshToken: string | null): Promise<null> {
    return request<null>({
      url: '/auth/logout',
      method: 'post',
      data: { refresh_token: refreshToken },
    })
  },

  me(): Promise<CurrentUser> {
    return request<CurrentUser>({ url: '/auth/me' })
  },

  changePassword(payload: ChangePasswordPayload): Promise<TokenBundle> {
    return request<TokenBundle>({
      url: '/auth/change-password',
      method: 'post',
      data: payload,
    })
  },
}
