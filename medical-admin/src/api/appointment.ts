import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export interface Appointment {
  id: number
  patient_id: number
  doctor_id: number
  department_id: number
  appointment_time: string
  status: string
  padded_id?: string
  patient_name?: string
  department_name?: string
  report_count: number
  reports: AppointmentReport[]
}

export interface AppointmentReport {
  id: number
  type: string
  content: Record<string, unknown>
  ai_interpretation?: string
  interpretation_status: 'pending' | 'completed' | 'failed'
  created_at: string
}

export function listMyAppointments(
  page = 1,
  perPage = 20,
  statusFilter?: string
): Promise<PaginationResponse<Appointment>> {
  return request.get('/appointments', { params: { page, per_page: perPage, status_filter: statusFilter } })
}

export function updateAppointmentStatus(id: number, status: string): Promise<Appointment> {
  return request.put(`/appointments/${id}`, { status })
}
