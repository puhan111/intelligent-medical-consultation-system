import request from '../utils/request'
import type { LoginRequest, TokenResponse } from '../types/api'

export function login(data: LoginRequest): Promise<TokenResponse> {
  return request.post('/auth/login', data)
}
