import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export interface PrescriptionItem {
  id: number
  drug_name: string
  dosage: string
  quantity: number
  unit_price?: number
  subtotal?: number
  is_selected: boolean
}

/** 处方账单状态：none 未生成 / unpaid 待支付 / paid 已支付 */
export type PrescriptionBillStatus = 'none' | 'unpaid' | 'paid'

export interface Prescription {
  id: number
  appointment_id: number
  status: 'pending' | 'dispensed'
  padded_id?: string
  doctor_name?: string
  department_name?: string
  items: PrescriptionItem[]
  selected_total: number
  bill_status: PrescriptionBillStatus
  bill_id?: number
  can_modify_selection: boolean
  created_at: string
  updated_at: string
}

export function listMyPrescriptions(
  page = 1,
  perPage = 10
): Promise<PaginationResponse<Prescription>> {
  return request.get('/prescriptions', { params: { page, per_page: perPage } })
}

export function getPrescription(id: number): Promise<Prescription> {
  return request.get(`/prescriptions/${id}`)
}

/** 勾选或取消勾选某项药品，取消视为拒药 */
export function updateItemSelection(
  prescriptionId: number,
  itemId: number,
  isSelected: boolean
): Promise<Prescription> {
  return request.put(`/prescriptions/${prescriptionId}/items/${itemId}/selection`, {
    is_selected: isSelected,
  })
}

/** 按已勾选药品生成药费账单，返回的 bill_id 用于支付 */
export function createPrescriptionBill(prescriptionId: number): Promise<Prescription> {
  return request.post(`/prescriptions/${prescriptionId}/bill`)
}
