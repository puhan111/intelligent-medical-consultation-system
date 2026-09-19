import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export interface Department {
  id: number
  name: string
  description?: string
  padded_id?: string
  created_at: string
  updated_at: string
}

export function listDepartments(page = 1, perPage = 50): Promise<PaginationResponse<Department>> {
  return request.get('/departments', { params: { page, per_page: perPage } })
}

export function getDepartment(id: number): Promise<Department> {
  return request.get(`/departments/${id}`)
}
