import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export type BillStatus = 'unpaid' | 'paid'
export type PaymentOrderStatus = 'pending' | 'success' | 'failed'
export type BillType = 'consultation' | 'prescription'

export interface BillItem {
  item_type: 'consultation' | 'medication'
  name: string
  unit_price: number
  quantity: number
  subtotal: number
}

export interface Bill {
  id: number
  appointment_id: number
  amount: number
  status: BillStatus
  bill_type: BillType
  prescription_id?: number
  paid_at?: string
  payment_method?: 'online' | 'cash' | 'card'
  paid_by_type?: 'patient' | 'cashier'
  padded_id?: string
  items: BillItem[]
  created_at: string
  updated_at: string
}

export interface PaymentOrder {
  order_no: string
  amount: number
  channel: string
  status: PaymentOrderStatus
  fail_reason?: string
  paid_at?: string
}

export function listMyBills(page = 1, perPage = 10): Promise<PaginationResponse<Bill>> {
  return request.get('/bills', { params: { page, per_page: perPage } })
}

/** 发起线上支付，返回 pending 流水，需轮询 getPaymentStatus 获取结果 */
export function payBill(id: number): Promise<PaymentOrder> {
  return request.post(`/bills/${id}/pay`)
}

export function getPaymentStatus(id: number): Promise<PaymentOrder> {
  return request.get(`/bills/${id}/payment-status`)
}
