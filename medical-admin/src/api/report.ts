import request from '../utils/request'
import type { PaginationResponse } from '../types/api'

export interface ReportPatient {
  id: number
  email: string
  first_name?: string
  last_name?: string
  gender?: string
}

export interface ReportCreate {
  patient_id: number
  appointment_id: number
  type: string
  content: ReportContent
}

export interface ReportItem {
  name: string
  code?: string
  value: string
  unit?: string
  reference_range?: string
  status?: 'normal' | 'high' | 'low' | 'critical' | 'abnormal'
}

export interface ReportContent {
  items: ReportItem[]
  conclusion?: string
}

export interface ExamPendingAppointment {
  id: number
  patient_id: number
  patient_name?: string
  patient_email?: string
  department_name?: string
  doctor_name?: string
  appointment_time: string
  status: 'waiting_exam'
  report_count: number
}

export interface Report {
  id: number
  patient_id: number
  appointment_id?: number
  type: string
  content: Record<string, any>
  ai_interpretation?: string
  interpretation_status: string
  padded_id?: string
}

export function createReport(data: ReportCreate): Promise<Report> {
  return request.post('/reports', data)
}

export function uploadReportCsv(data: FormData): Promise<Report> {
  return request.post('/reports/upload-csv', data, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listReportPatients(
  page = 1,
  perPage = 10,
  keyword?: string,
): Promise<PaginationResponse<ReportPatient>> {
  return request.get('/reports/patients', {
    params: { page, per_page: perPage, keyword: keyword || undefined },
  })
}

export function listExamPendingAppointments(
  page = 1,
  perPage = 10,
  keyword?: string,
): Promise<PaginationResponse<ExamPendingAppointment>> {
  return request.get('/reports/exam-pending', {
    params: { page, per_page: perPage, keyword: keyword || undefined },
  })
}
