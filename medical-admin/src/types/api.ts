// 通用API响应结构
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 分页响应
export interface PaginationResponse<T> {
  items: T[]
  total: number
  per_page: number
  current_page: number
  last_page: number
  has_more: boolean
}

// 管理员登录
export interface LoginRequest {
  email: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// 科室
export interface Department {
  id: number
  name: string
  description?: string
  created_at: string
  updated_at: string
}

export interface DepartmentImportRequest {
  content: string
}

export interface DepartmentImportResult {
  created: string[]
  skipped: string[]
}

// 知识库
export interface KnowledgeUploadRequest {
  source: string
  content: string
  source_type: string
}

export interface KnowledgeDocument {
  source: string
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface KnowledgeCategory {
  source_type: string
  document_count: number
  chunk_count: number
  documents: KnowledgeDocument[]
}

export interface KnowledgeLibrary {
  document_count: number
  chunk_count: number
  categories: KnowledgeCategory[]
}

// 管理员
export interface Admin {
  id: number
  email: string
  first_name?: string
  last_name?: string
  is_active: boolean
  role?: string
  padded_id?: string
}

export interface AdminCreate {
  email: string
  password: string
  first_name?: string
  last_name?: string
  is_active?: boolean
  role?: string
}

export interface AdminUpdate {
  email?: string
  first_name?: string
  last_name?: string
  password?: string
  is_active?: boolean
}
