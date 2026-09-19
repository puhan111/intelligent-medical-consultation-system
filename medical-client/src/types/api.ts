// 通用 API 响应结构
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 分页响应
export interface PaginationResponse<T> {
  items: T[]
  total: number
  per_page: number
  current_page: number
  last_page: number
  has_more: boolean
}

// 患者账号
export interface User {
  id: number
  email: string
  first_name?: string
  last_name?: string
  avatar?: string
  gender?: string
  is_active: boolean
  is_verified: boolean
  padded_id?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  first_name: string
  last_name: string
}
