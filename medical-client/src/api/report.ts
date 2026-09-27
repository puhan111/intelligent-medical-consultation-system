import request from '../utils/request'
import { clearToken, getToken } from '../utils/request'
import type { PaginationResponse } from '../types/api'
import { readNdjsonStream } from '../utils/ndjsonStream'

export type InterpretationStatus = 'pending' | 'completed' | 'failed'

/** 报告单项指标。后端 content 为自由 JSON，这是检验科录入时约定的结构 */
export interface ReportItem {
  name: string
  value: string
  unit?: string
  reference_range?: string
  status?: string
}

export interface Report {
  id: number
  appointment_id?: number
  type: string
  content: { items?: ReportItem[] } & Record<string, any>
  ai_interpretation?: string
  interpretation_status: InterpretationStatus
  interpretation_at?: string
  padded_id?: string
  created_at: string
  updated_at: string
}

export function listMyReports(page = 1, perPage = 10): Promise<PaginationResponse<Report>> {
  return request.get('/reports', { params: { page, per_page: perPage } })
}

export interface ReportChatResponse {
  session_id: string
  message: string
  turn_count: number
}

/**
 * 就某份已解读完成的报告追问
 * 首轮不传 sessionId，之后带上返回值以延续上下文
 */
export function chatAboutReport(
  reportId: number,
  message: string,
  sessionId?: string
): Promise<ReportChatResponse> {
  return request.post(`/reports/${reportId}/chat`, {
    message,
    session_id: sessionId,
  })
}

export type ReportChatStreamEvent =
  | { type: 'start'; session_id: string; turn_count: number }
  | { type: 'delta'; content: string }
  | { type: 'replace'; content: string }
  | { type: 'done'; session_id: string; turn_count: number }
  | { type: 'error'; message: string }

export async function chatAboutReportStream(
  reportId: number,
  message: string,
  sessionId: string | undefined,
  onEvent: (event: ReportChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = getToken()
  const response = await fetch(`/api/v1/reports/${reportId}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({ message, session_id: sessionId }),
    signal,
  })

  if (!response.ok) {
    let errorMessage = '报告追问请求失败'
    try {
      const body = await response.json()
      errorMessage = body.message || body.detail || errorMessage
    } catch {
      // 非 JSON 错误响应沿用通用文案
    }
    if (response.status === 401 || response.status === 403) {
      clearToken()
      window.location.href = '/login'
    }
    throw new Error(errorMessage)
  }
  await readNdjsonStream<ReportChatStreamEvent>(response.body, onEvent)
}
