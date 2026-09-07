import { chatFetch, authHeaders, CHAT_BASE } from './client'
import type { Citation, SessionOut } from '../types'

export async function listSessions() {
  return (await chatFetch('/api/v1/sessions')) as SessionOut[]
}

export async function createSession(title?: string) {
  return (await chatFetch('/api/v1/sessions', {
    method: 'POST',
    body: JSON.stringify({ title: title || undefined }),
  })) as SessionOut
}

export async function deleteSession(id: string) {
  await chatFetch('/api/v1/sessions/' + id, { method: 'DELETE' })
}

export type StreamHandlers = {
  onCitation?: (c: Citation) => void
  onToken?: (t: string) => void
  onError?: (msg: string) => void
  onDone?: () => void
}

export async function streamChat(sessionId: string, message: string, handlers: StreamHandlers) {
  const res = await fetch(CHAT_BASE + '/api/v1/chat/stream', {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ session_id: sessionId, message }),
  })
  if (!res.ok || !res.body) {
    const t = await res.text()
    throw new Error(t || res.statusText)
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buf = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })
    const parts = buf.split('\n\n')
    buf = parts.pop() || ''
    for (const part of parts) {
      const lines = part.split('\n')
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
          handlers.onDone?.()
        }
      } catch {
        if (event === 'token') handlers.onToken?.(data)
      }
    }
  }
  handlers.onDone?.()
}
