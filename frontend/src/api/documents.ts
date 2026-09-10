import { apiFetch, apiUrl, authHeaders, handleUnauthorized } from './client'
import type { DocumentListResponse } from '../types'

export const ALLOWED_UPLOAD_EXT = ['.txt', '.md', '.markdown', '.pdf', '.docx']
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024
export const SYNC_THRESHOLD_BYTES = 1 * 1024 * 1024

export function validateUploadFile(file: File): string | null {
  const name = file.name.toLowerCase()
  const okExt = ALLOWED_UPLOAD_EXT.some((ext) => name.endsWith(ext))
  if (!okExt) {
    return '仅支持 ' + ALLOWED_UPLOAD_EXT.join(', ')
  }
  if (file.size <= 0) return '文件为空'
  if (file.size > MAX_UPLOAD_BYTES) return '文件不能超过 10MB'
  return null
}

export async function listDocuments(params?: {
  doc_type?: string
  status?: string
  offset?: number
  limit?: number
}) {
  const q = new URLSearchParams()
  if (params?.doc_type) q.set('doc_type', params.doc_type)
  if (params?.status) q.set('status', params.status)
  if (params?.offset != null) q.set('offset', String(params.offset))
  if (params?.limit != null) q.set('limit', String(params.limit))
  const qs = q.toString()
  const path = '/api/v1/documents' + (qs ? '?' + qs : '')
  return (await apiFetch(path)) as DocumentListResponse
}

export async function uploadDocument(file: File, doc_type = 'kb', sync?: boolean) {
  const err = validateUploadFile(file)
  if (err) throw new Error(err)
  const useSync = sync ?? file.size <= SYNC_THRESHOLD_BYTES
  const form = new FormData()
  form.append('file', file)
  form.append('doc_type', doc_type)
  form.append('sync', String(useSync))
  const res = await fetch(apiUrl('/api/v1/ingest'), {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  if (res.status === 401) {
    handleUnauthorized(401)
    throw new Error('未登录或登录已过期')
  }
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || res.statusText)
  }
  return res.json() as Promise<{ document_id: string; status: string; message: string; sync?: boolean }>
}
