import request from '../utils/request'
import type { KnowledgeLibrary, KnowledgeUploadRequest } from '../types/api'

export function getKnowledgeLibrary(): Promise<KnowledgeLibrary> {
  return request.get('/knowledge')
}

export function uploadKnowledge(data: KnowledgeUploadRequest): Promise<void> {
  return request.post('/knowledge', data)
}
