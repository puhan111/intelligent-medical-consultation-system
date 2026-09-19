import request from '../utils/request'

export interface MedicalRecordCreate {
  appointment_id: number
  diagnosis: string
  content?: string
}

export interface MedicalRecord {
  id: number
  appointment_id: number
  patient_id: number
  doctor_id: number
  diagnosis: string
  content?: string
  padded_id?: string
  patient_name?: string
}

export function createMedicalRecord(data: MedicalRecordCreate): Promise<MedicalRecord> {
  return request.post('/medical-records', data)
}
