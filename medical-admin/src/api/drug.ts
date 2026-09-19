import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export interface Drug {
  id: number
  name: string
  spec?: string
  unit: string
  unit_price: number
  is_active: boolean
  padded_id?: string
  created_at: string
  updated_at: string
}

export interface DrugCreate {
  name: string
  spec?: string
  unit: string
  unit_price: number
  is_active?: boolean
}

export interface DrugUpdate {
  name?: string
  spec?: string
  unit?: string
  unit_price?: number
  is_active?: boolean
}

export function listDrugs(
  page = 1,
  perPage = 20,
  keyword?: string,
  isActive?: boolean
): Promise<PaginationResponse<Drug>> {
  const params: Record<string, any> = { page, per_page: perPage }
  if (keyword) params.keyword = keyword
  if (isActive !== undefined) params.is_active = isActive
  return request.get('/drugs', { params })
}

export function createDrug(data: DrugCreate): Promise<Drug> {
  return request.post('/drugs', data)
}

export function updateDrug(id: number, data: DrugUpdate): Promise<Drug> {
  return request.put(`/drugs/${id}`, data)
}

/** 停用药品（软删除，历史处方仍可正常显示） */
export function deactivateDrug(id: number): Promise<void> {
  return request.delete(`/drugs/${id}`)
}
