import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export type AppointmentStatus = 'pending' | 'confirmed' | 'waiting_exam' | 'completed' | 'cancelled'

export interface Appointment {
  id: number
  patient_id: number
  doctor_id: number
  department_id: number
  appointment_time: string
  status: AppointmentStatus
  padded_id?: string
  doctor_name?: string
  department_name?: string
  created_at: string
  updated_at: string
}

export interface AppointmentCreate {
  doctor_id: number
  department_id: number
  /** ISO 8601 格式 */
  appointment_time: string
}

export function createAppointment(data: AppointmentCreate): Promise<Appointment> {
  return request.post('/appointments', data)
}

export function listMyAppointments(page = 1, perPage = 10): Promise<PaginationResponse<Appointment>> {
  return request.get('/appointments', { params: { page, per_page: perPage } })
}

export function cancelAppointment(id: number): Promise<void> {
  return request.delete(`/appointments/${id}`)
}
