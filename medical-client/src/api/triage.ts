import request from '../utils/request'
import { clearToken, getToken } from '../utils/request'
import { readNdjsonStream } from '../utils/ndjsonStream'

export interface DepartmentRecommendation {
  department_id: number
  department_name: string
  confidence: 'high' | 'medium' | 'low'
}

export interface TriageChatRequest {
  message: string
  session_id?: string
}

export interface TriageChatResponse {
  session_id: string
  message: string
  recommendations: DepartmentRecommendation[]
  turn_count: number
}

export function triageChat(data: TriageChatRequest): Promise<TriageChatResponse> {
  return request.post('/triage/chat', data)
}

export type TriageStreamEvent =
  | { type: 'start'; session_id: string; turn_count: number }
  | { type: 'delta'; content: string }
  | { type: 'replace'; content: string }
  | { type: 'done'; session_id: string; turn_count: number; recommendations: DepartmentRecommendation[] }
  | { type: 'error'; message: string }

export async function triageChatStream(
  data: TriageChatRequest,
  onEvent: (event: TriageStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken()
  const response = await fetch('/api/v1/triage/chat/stream', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(data),
    signal,
  })

  if (!response.ok) {
    let message = '智能分诊请求失败'
    try {
      const body = await response.json()
      message = body.message || body.detail || message
    } catch {
      // 非 JSON 错误响应沿用通用文案
    }
    if (response.status === 401 || response.status === 403) {
      clearToken()
      window.location.href = '/login'
    }
    throw new Error(message)
  }

  await readNdjsonStream<TriageStreamEvent>(response.body, onEvent)
}
