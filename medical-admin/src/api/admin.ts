import request from '../utils/request'
import type { Admin, AdminCreate, AdminUpdate, PaginationResponse } from '../types/api'

export function listAdmins(page = 1, perPage = 20): Promise<PaginationResponse<Admin>> {
  return request.get('/admins', { params: { page, per_page: perPage } })
}

export function getAdmin(id: number): Promise<Admin> {
  return request.get(`/admins/${id}`)
}

export function createAdmin(data: AdminCreate): Promise<Admin> {
  return request.post('/admins', data)
}

export function updateAdmin(id: number, data: AdminUpdate): Promise<void> {
  return request.put(`/admins/${id}`, data)
}

export function deleteAdmin(id: number): Promise<void> {
  return request.delete(`/admins/${id}`)
}

export function resetAdminPassword(id: number, password: string): Promise<void> {
  return request.post(`/admins/${id}/reset-password`, { password })
}

export function changeAdminPassword(id: number, currentPassword: string, newPassword: string): Promise<void> {
  return request.post(`/admins/${id}/change-password`, {
    current_password: currentPassword,
    new_password: newPassword,
  })
}
