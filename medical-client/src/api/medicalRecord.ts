import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export interface MedicalRecord {
  id: number
  appointment_id: number
  doctor_id: number
  diagnosis: string
  content?: string
  padded_id?: string
  doctor_name?: string
  created_at: string
  updated_at: string
}

export function listMyMedicalRecords(
  page = 1,
  perPage = 10
): Promise<PaginationResponse<MedicalRecord>> {
  return request.get('/medical-records', { params: { page, per_page: perPage } })
}
