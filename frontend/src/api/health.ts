import { chatFetch, CHAT_BASE } from './client'

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

export type LlmConfigResponse = {
  base_url: string
  model: string
  api_key_set: boolean
}

export type LlmConfigUpdate = {
  base_url: string
  model: string
  /** undefined = keep existing; '' = clear to sk-no-auth; non-empty = set */
  api_key?: string
}

export async function fetchHealth(): Promise<HealthResponse> {
  const res = await fetch(CHAT_BASE + '/api/v1/health')
  if (!res.ok) throw new Error('health ' + res.status)
  return res.json()
}

export async function fetchLlmConfig(): Promise<LlmConfigResponse> {
  return (await chatFetch('/api/v1/llm/config')) as LlmConfigResponse
}

export async function updateLlmConfig(cfg: LlmConfigUpdate): Promise<LlmConfigResponse> {
  const body: Record<string, string> = {
    base_url: cfg.base_url,
    model: cfg.model,
  }
  if (cfg.api_key !== undefined) {
    body.api_key = cfg.api_key
  }
  return (await chatFetch('/api/v1/llm/config', {
    method: 'PUT',
    body: JSON.stringify(body),
  })) as LlmConfigResponse
}
