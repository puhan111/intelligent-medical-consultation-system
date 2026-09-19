import request from '../utils/request'
import type { Department, DepartmentImportResult, PaginationResponse } from '../types/api'

export interface DepartmentCreate {
  name: string
  description?: string
}

export interface DepartmentUpdate {
  name?: string
  description?: string
}

export function listDepartments(page = 1, perPage = 50): Promise<PaginationResponse<Department>> {
  return request.get('/departments', { params: { page, per_page: perPage } })
}

export function createDepartment(data: DepartmentCreate): Promise<Department> {
  return request.post('/departments', data)
}

export function updateDepartment(id: number, data: DepartmentUpdate): Promise<Department> {
  return request.put(`/departments/${id}`, data)
}

export function importDepartmentsFromMarkdown(content: string): Promise<DepartmentImportResult> {
  return request.post('/departments/import-md', { content })
}

export function deleteDepartment(id: number): Promise<void> {
  return request.delete(`/departments/${id}`)
}
