import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export interface Bill {
  id: number
  patient_id: number
  appointment_id: number
  amount: number
  status: string
  paid_at?: string
  payment_method?: string
  paid_by_type?: string
  cashier_id?: number
  padded_id?: string
  patient_name?: string
  cashier_name?: string
}

export function listBills(
  page = 1,
  perPage = 20,
  statusFilter?: 'unpaid' | 'paid'
): Promise<PaginationResponse<Bill>> {
  const params: any = { page, per_page: perPage }
  if (statusFilter) params.status_filter = statusFilter
  return request.get('/bills', { params })
}

export function settleBill(id: number): Promise<Bill> {
  return request.post(`/bills/${id}/settle`)
}
