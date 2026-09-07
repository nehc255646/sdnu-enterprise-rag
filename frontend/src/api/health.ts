import { CHAT_BASE } from './client'

export type HealthDependency = {
  name: string
  ok: boolean
  detail?: string | null
}

export type HealthResponse = {
  status: string
  service?: string
  dependencies?: HealthDependency[]
  embedding_provider?: string | null
  embedding_model?: string | null
  llm_base_url?: string | null
  llm_model?: string | null
  retrieval_backend?: string | null
}

export type LlmConfig = {
  base_url: string
  model: string
  api_key?: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(CHAT_BASE + '/api/v1/health')
  if (!res.ok) throw new Error('health ' + res.status)
  return res.json()
}

/** Runtime LLM override — requires backend2 PUT /api/v1/llm/config */
export async function updateLlmConfig(cfg: LlmConfig, token?: string, tenantId?: string) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = 'Bearer ' + token
  if (tenantId) headers['X-Tenant-Id'] = tenantId
  const res = await fetch(CHAT_BASE + '/api/v1/llm/config', {
    method: 'PUT',
    headers,
    body: JSON.stringify({
      base_url: cfg.base_url,
      model: cfg.model,
      api_key: cfg.api_key || undefined,
    }),
  })
  if (res.status === 404) {
    const err = new Error('LLM_CONFIG_API_MISSING')
    throw err
  }
  if (!res.ok) {
    const t = await res.text()
    throw new Error(t || res.statusText)
  }
  return res.json()
}
