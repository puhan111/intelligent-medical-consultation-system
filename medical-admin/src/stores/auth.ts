import { ref } from 'vue'
import { getAdmin } from '../api/admin'
import { getToken } from '../utils/request'
import type { Admin } from '../types/api'

export const currentAdmin = ref<Admin | null>(null)

function decodeAdminIdFromToken(token: string): number | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return Number(payload.sub)
  } catch {
    return null
  }
}

export async function loadCurrentAdmin(): Promise<Admin | null> {
  const token = getToken()
  if (!token) {
    currentAdmin.value = null
    return null
  }
  const adminId = decodeAdminIdFromToken(token)
  if (!adminId) {
    currentAdmin.value = null
    return null
  }
  currentAdmin.value = await getAdmin(adminId)
  return currentAdmin.value
}

export function clearCurrentAdmin(): void {
  currentAdmin.value = null
}
