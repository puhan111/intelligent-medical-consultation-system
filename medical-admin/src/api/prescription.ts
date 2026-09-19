import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export interface PrescriptionItemCreate {
  /** 从药品目录选药，后端据此快照药名与单价 */
  drug_id?: number
  /** 仅在无法从目录选择时使用，此时无价格 */
  drug_name?: string
  dosage: string
  quantity: number
}

export interface PrescriptionCreate {
  appointment_id: number
  items: PrescriptionItemCreate[]
}

export interface PrescriptionItem {
  id: number
  drug_name: string
  dosage: string
  quantity: number
  drug_id?: number
  unit_price?: number
  is_selected: boolean
  subtotal?: number
}

export interface Prescription {
  id: number
  appointment_id: number
  doctor_id: number
  status: string
  padded_id?: string
  doctor_name?: string
  patient_name?: string
  items: PrescriptionItem[]
  total_amount?: number
}

export function createPrescription(data: PrescriptionCreate): Promise<Prescription> {
  return request.post('/prescriptions', data)
}

export function listPendingPrescriptions(page = 1, perPage = 20): Promise<PaginationResponse<Prescription>> {
  return request.get('/prescriptions', { params: { page, per_page: perPage } })
}

export function dispensePrescription(id: number): Promise<Prescription> {
  return request.post(`/prescriptions/${id}/dispense`)
}
