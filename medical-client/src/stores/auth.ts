import { ref } from 'vue'
import { clearToken, getToken } from '../utils/request'
import { getMyProfile } from '../api/user'
import type { User } from '../types/api'

export const currentUser = ref<User | null>(null)

/**
 * 从后端加载当前登录患者的完整信息
 */
export async function loadCurrentUser(): Promise<User | null> {
  const token = getToken()
  if (!token) {
    currentUser.value = null
    return null
  }
  try {
    currentUser.value = await getMyProfile()
    return currentUser.value
  } catch {
    currentUser.value = null
    return null
  }
}

export function clearCurrentUser(): void {
  currentUser.value = null
  clearToken()
}
