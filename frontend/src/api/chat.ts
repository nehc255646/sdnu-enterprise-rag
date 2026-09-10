import { apiFetch, apiUrl, authHeaders, handleUnauthorized } from './client'
import type { Citation, SessionOut, SessionWithMessages } from '../types'

export async function listSessions() {
  return (await apiFetch('/api/v1/sessions')) as SessionOut[]
}

export async function createSession(title?: string) {
  return (await apiFetch('/api/v1/sessions', {
    method: 'POST',
    body: JSON.stringify({ title: title || undefined }),
  })) as SessionOut
}

export async function getSession(id: string) {
  return (await apiFetch('/api/v1/sessions/' + id)) as SessionWithMessages
}

export async function deleteSession(id: string) {
  await apiFetch('/api/v1/sessions/' + id, { method: 'DELETE' })
}

export type StreamHandlers = {
  onCitation?: (c: Citation) => void
  onToken?: (t: string) => void
  onError?: (msg: string) => void
  onDone?: () => void
}

export async function streamChat(
  sessionId: string,
  message: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
) {
  const res = await fetch(apiUrl('/api/v1/chat/stream'), {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  })
  if (res.status === 401) {
    handleUnauthorized(401)
    throw new Error('未登录或登录已过期')
  }
  if (!res.ok || !res.body) {
    const t = await res.text()
    throw new Error(t || res.statusText)
  }

  let finished = false
  const finish = () => {
    if (finished) return
    finished = true
    handlers.onDone?.()
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  const nl = String.fromCharCode(10)
  const sep = nl + nl
  try {
    while (true) {
      if (signal?.aborted) {
        await reader.cancel()
        break
      }
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const parts = buf.split(sep)
      buf = parts.pop() || ''
      for (const part of parts) {
        const lines = part.split(nl)
        let event = 'message'
        let data = ''
        for (const line of lines) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) data += line.slice(5).trim()
        }
        if (!data) continue
        try {
          if (event === 'citation') handlers.onCitation?.(JSON.parse(data))
          else if (event === 'token') {
            const parsed = JSON.parse(data)
            const tok = typeof parsed === 'string' ? parsed : (parsed.token ?? parsed.text ?? String(parsed))
            handlers.onToken?.(tok)
          } else if (event === 'error') {
            const parsed = JSON.parse(data)
            handlers.onError?.(parsed.message || parsed.detail || JSON.stringify(parsed))
          } else if (event === 'done') {
            finish()
          }
        } catch {
          if (event === 'token') handlers.onToken?.(data)
        }
      }
    }
  } catch (e) {
    if (signal?.aborted || (e instanceof DOMException && e.name === 'AbortError')) {
      return
    }
    throw e
  }
  if (!signal?.aborted) finish()
}
