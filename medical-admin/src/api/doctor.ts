import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export interface Doctor {
  id: number
  admin_id: number
  department_id: number
  title?: string
  introduction?: string
  padded_id?: string
  first_name?: string
  last_name?: string
  email?: string
  department_name?: string
}

export interface DoctorCreate {
  department_id: number
  title?: string
  introduction?: string
  email: string
  password: string
  first_name?: string
  last_name?: string
}

export interface DoctorUpdate {
  department_id?: number
  title?: string
  introduction?: string
}

export function listDoctors(page = 1, perPage = 20, departmentId?: number): Promise<PaginationResponse<Doctor>> {
  return request.get('/doctors', { params: { page, per_page: perPage, department_id: departmentId } })
}

export function createDoctor(data: DoctorCreate): Promise<Doctor> {
  return request.post('/doctors', data)
}

export function updateDoctor(id: number, data: DoctorUpdate): Promise<Doctor> {
  return request.put(`/doctors/${id}`, data)
}

export function deleteDoctor(id: number): Promise<void> {
  return request.delete(`/doctors/${id}`)
}
