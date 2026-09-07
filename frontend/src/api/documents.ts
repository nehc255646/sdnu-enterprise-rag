import { ingestFetch, authHeaders, INGEST_BASE } from './client'
import type { DocumentListResponse } from '../types'

export async function listDocuments(params?: { doc_type?: string; status?: string }) {
  const q = new URLSearchParams()
  if (params?.doc_type) q.set('doc_type', params.doc_type)
  if (params?.status) q.set('status', params.status)
  const qs = q.toString()
  const path = '/api/v1/documents' + (qs ? '?' + qs : '')
  return (await ingestFetch(path)) as DocumentListResponse
}

export async function uploadDocument(file: File, doc_type = "kb", sync = true) {
  const form = new FormData()
  form.append('file', file)
  form.append('doc_type', doc_type)
  form.append('sync', String(sync))
  const res = await fetch(INGEST_BASE + "/api/v1/ingest", {
    method: 'POST',
    headers: authHeaders(),
    body: form,
  })
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || res.statusText)
  }
  return res.json()
}
