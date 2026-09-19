import request from '../utils/request'

export interface UserProfile {
  id: number
  email: string
  first_name?: string
  last_name?: string
  avatar?: string
  gender?: string
  is_active: boolean
  is_verified: boolean
  padded_id?: string
  created_at: string
  updated_at: string
}

export interface UserProfileUpdate {
  first_name?: string
  last_name?: string
  avatar?: string
  gender?: string
}

export function getMyProfile(): Promise<UserProfile> {
  return request.get('/users/me')
}

export function updateMyProfile(data: UserProfileUpdate): Promise<UserProfile> {
  return request.put('/users/me', data)
}
