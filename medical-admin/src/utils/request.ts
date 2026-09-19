import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import type { ApiResponse } from '../types/api'

const TOKEN_KEY = 'admin_access_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1/backoffice',
  timeout: 30000,
})

request.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 后台鉴权失败（token 无效/过期/账号停用）返回的是 403，与「权限不足」同码，
// 只能靠 message 区分：前者需要重新登录，后者只是当前角色无权访问该接口。
const AUTH_FAILURE_MESSAGES = [
  'Invalid authentication credentials',
  'Inactive admin',
  'Not authenticated',
]

function isAuthFailure(status?: number, message?: string): boolean {
  if (status === 401) return true
  if (status !== 403) return false
  return AUTH_FAILURE_MESSAGES.some((m) => message?.includes(m))
}

request.interceptors.response.use(
  (response) => {
    const body = response.data as ApiResponse
    return body.data
  },
  (error) => {
    const message = error?.response?.data?.message || error.message || '请求失败'
    ElMessage.error(message)

    if (isAuthFailure(error?.response?.status, error?.response?.data?.message)) {
      clearToken()
      // 已在登录页时不再跳转，避免刷新循环
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  }
)

export default request
