const INGEST_BASE = (import.meta.env.VITE_INGEST_API as string) || '/ingest-api'
const CHAT_BASE = (import.meta.env.VITE_CHAT_API as string) || '/chat-api'

const AUTH_KEY = 'sdnu_rag_auth'

export type StoredAuth = {
  access_token: string
  tenant_id: string
  user_id: string
  email?: string
}

export function loadAuth(): StoredAuth | null {
  const raw = localStorage.getItem(AUTH_KEY)
  if (!raw) return null
  try { return JSON.parse(raw) as StoredAuth } catch { return null }
}

export function saveAuth(auth: StoredAuth) {
  localStorage.setItem(AUTH_KEY, JSON.stringify(auth))
}

export function clearAuth() {
  localStorage.removeItem(AUTH_KEY)
}

function authHeaders(extra?: HeadersInit): Headers {
  const h = new Headers(extra)
  const auth = loadAuth()
  if (auth?.access_token) h.set('Authorization', `Bearer ${auth.access_token}`)
  if (auth?.tenant_id) h.set('X-Tenant-Id', auth.tenant_id)
  return h
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') return data.detail
    return JSON.stringify(data?.detail ?? data)
  } catch {
    return res.statusText || `HTTP ${res.status}`
  }
}

export async function chatFetch(path: string, init: RequestInit = {}) {
  const headers = authHeaders(init.headers)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(`${CHAT_BASE}${path}`, { ...init, headers })
  if (!res.ok) throw new Error(await parseError(res))
  if (res.status === 204) return null
  const ct = res.headers.get('content-type') || ''
  if (ct.includes('application/json')) return res.json()
  return res
}

export async function ingestFetch(path: string, init: RequestInit = {}) {
  const headers = authHeaders(init.headers)
  const res = await fetch(`${INGEST_BASE}${path}`, { ...init, headers })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export { INGEST_BASE, CHAT_BASE, authHeaders }
