import request from '../utils/request'

export interface Doctor {
  id: number
  department_id: number
  title?: string
  introduction?: string
  padded_id?: string
  first_name?: string
  last_name?: string
  department_name?: string
  created_at: string
  updated_at: string
}

/** 患者端医生列表接口不分页，直接返回数组 */
export function listDoctors(departmentId?: number): Promise<Doctor[]> {
  return request.get('/doctors', { params: { department_id: departmentId } })
}

export function getDoctor(id: number): Promise<Doctor> {
  return request.get(`/doctors/${id}`)
}
