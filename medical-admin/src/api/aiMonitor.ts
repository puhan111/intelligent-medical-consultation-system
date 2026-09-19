import request from '../utils/request'

export type AgentType = 'triage' | 'report_interpret' | 'report_followup' | 'eval_judge'

export interface AiMonitorOverview {
  period: {
    days: number
    start_date: string
    end_date: string
    agent_type: AgentType | null
  }
  metrics: {
    call_count: number
    token_count: number
    average_latency_ms: number
    success_count: number
    error_count: number
    timeout_count: number
    success_rate: number
    rag_query_count: number
    rag_average_latency_ms: number
  }
  budget: {
    available: boolean
    used: number | null
    limit: number
    usage_rate: number | null
  }
  trend: Array<{
    date: string
    calls: number
    tokens: number
    rag_queries: number
  }>
  agent_breakdown: Array<{
    agent_type: string
    count: number
  }>
  recent_llm_calls: Array<{
    id: number
    agent_type: string
    input_tokens: number
    output_tokens: number
    latency_ms: number
    status: string
    error_message?: string | null
    created_at: string
  }>
  recent_rag_queries: Array<{
    id: number
    agent_type?: string | null
    query: string
    top_k: number
    result_count: number
    latency_ms: number
    created_at: string
  }>
}

export function getAiMonitorOverview(params: {
  days: 7 | 14 | 30
  agent_type?: AgentType
}): Promise<AiMonitorOverview> {
  return request.get('/ai-monitor/overview', { params })
}
