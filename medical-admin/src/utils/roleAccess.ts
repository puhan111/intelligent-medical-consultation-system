export type BackofficeRole = 'superadmin' | 'admin' | 'doctor' | 'pharmacist' | 'cashier' | 'lab'

export const roleLabels: Record<BackofficeRole, string> = {
  superadmin: '超级管理员',
  admin: '管理员',
  doctor: '医生',
  pharmacist: '药师',
  cashier: '收费员',
  lab: '检验科',
}

export const roleHomePaths: Record<BackofficeRole, string> = {
  superadmin: '/departments',
  admin: '/profile',
  doctor: '/my-appointments',
  pharmacist: '/prescriptions',
  cashier: '/bills',
  lab: '/reports',
}

export function isBackofficeRole(role?: string): role is BackofficeRole {
  return Boolean(role && role in roleHomePaths)
}

export function getRoleHomePath(role?: string): string {
  return isBackofficeRole(role) ? roleHomePaths[role] : '/login'
}

export function getRoleLabel(role?: string): string {
  return isBackofficeRole(role) ? roleLabels[role] : '未知角色'
}
