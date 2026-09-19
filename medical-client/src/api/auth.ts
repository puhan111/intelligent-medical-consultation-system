import request from '../utils/request'
import type { LoginRequest, RegisterRequest, TokenResponse } from '../types/api'

export interface RegisterResult {
  user_id: number
  email: string
}

export function register(data: RegisterRequest): Promise<RegisterResult> {
  return request.post('/auth/register', data)
}

export function login(data: LoginRequest): Promise<TokenResponse> {
  return request.post('/auth/login', data)
}

export function logout(refreshToken: string): Promise<void> {
  return request.post('/auth/logout', { refresh_token: refreshToken })
}
