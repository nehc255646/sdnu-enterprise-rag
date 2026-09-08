import { useEffect, useRef, useState } from 'react'
import { Button, Card, Input, List, Space, Typography, message, Spin, Collapse, Empty, theme } from 'antd'
import { PlusOutlined, SendOutlined, DeleteOutlined } from '@ant-design/icons'
import { createSession, deleteSession, getSession, listSessions, streamChat } from '../api/chat'
import type { Citation, SessionOut } from '../types'

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Citation[]
}

function parseCitations(raw?: string | null): Citation[] {
  if (!raw) return []
  try {
    const v = JSON.parse(raw)
    return Array.isArray(v) ? v : []
  } catch {
    return []
  }
}

export default function ChatPage() {
  const { token } = theme.useToken()
  const [sessions, setSessions] = useState<SessionOut[]>([])
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loadingSessions, setLoadingSessions] = useState(false)
  const [loadingHistory, setLoadingHistory] = useState(false)
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const sendingRef = useRef(false)

  useEffect(() => { sessionIdRef.current = sessionId }, [sessionId])
  useEffect(() => { sendingRef.current = sending }, [sending])

  function abortStream() {
    abortRef.current?.abort()
    abortRef.current = null
  }

  async function loadHistory(id: string) {
    if (sendingRef.current) return
    setLoadingHistory(true)
    try {
      const detail = await getSession(id)
      if (sessionIdRef.current !== id || sendingRef.current) return
      setMessages(
        (detail.messages || []).map((m) => ({
          id: m.id,
          role: m.role === 'assistant' ? 'assistant' : 'user',
          content: m.content,
          citations: parseCitations(m.citations_json),
        })),
      )
    } catch (e) {
      if (sessionIdRef.current === id) {
        message.error(e instanceof Error ? e.message : '加载历史失败')
        setMessages([])
      }
    } finally {
      if (sessionIdRef.current === id) setLoadingHistory(false)
    }
  }

  async function refreshSessions(selectId?: string) {
    setLoadingSessions(true)
    try {
      const list = await listSessions()
      setSessions(list)
      const next = selectId || sessionIdRef.current || list[0]?.id || null
      setSessionId(next)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载会话失败')
    } finally {
      setLoadingSessions(false)
    }
  }

  useEffect(() => { void refreshSessions() }, [])

  useEffect(() => {
    if (sendingRef.current) return
    abortStream()
    setSending(false)
    if (!sessionId) {
      setMessages([])
      return
    }
    void loadHistory(sessionId)
    return () => {
      if (!sendingRef.current) abortStream()
    }
  }, [sessionId])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, sending])

  async function onNewSession() {
    try {
      abortStream()
      const s = await createSession('新对话')
      await refreshSessions(s.id)
      setSessionId(s.id)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '创建失败')
    }
  }

  async function onDelete(id: string) {
    try {
      if (sessionId === id) abortStream()
      await deleteSession(id)
      if (sessionId === id) {
        setSessionId(null)
        setMessages([])
      }
      await refreshSessions()
    } catch (e) {
      message.error(e instanceof Error ? e.message : '删除失败')
    }
  }

  async function onSend() {
    const text = input.trim()
    if (!text || sending) return
    let sid = sessionId
    sendingRef.current = true
    setSending(true)
    if (!sid) {
      try {
        const s = await createSession(text.slice(0, 20))
        sid = s.id
        setSessionId(sid)
        await refreshSessions(sid)
      } catch (e) {
        sendingRef.current = false
        setSending(false)
        message.error(e instanceof Error ? e.message : '创建会话失败')
        return
      }
    }

    abortStream()
    const controller = new AbortController()
    abortRef.current = controller

    const userMsg: ChatMessage = { id: 'u-' + Date.now(), role: 'user', content: text }
    const assistantId = 'a-' + Date.now()
    setMessages((prev) => [...prev, userMsg, { id: assistantId, role: 'assistant', content: '', citations: [] }])
    setInput('')

    const citations: Citation[] = []
    try {
      await streamChat(
        sid,
        text,
        {
          onCitation: (c) => {
            citations.push(c)
            setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, citations: [...citations] } : m))
          },
          onToken: (tok) => {
            setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: m.content + tok } : m))
          },
          onError: (msg) => {
            message.error(msg)
            setMessages((prev) => prev.map((m) => m.id === assistantId ? { ...m, content: m.content || ('错误: ' + msg) } : m))
          },
        },
        controller.signal,
      )
    } catch (e) {
      if (!(e instanceof DOMException && e.name === 'AbortError')) {
        message.error(e instanceof Error ? e.message : '对话失败')
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null
      sendingRef.current = false
      setSending(false)
    }
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16, minHeight: 'calc(100vh - 120px)' }}>
      <Card
        size="small"
        title="会话"
        extra={<Button size="small" icon={<PlusOutlined />} onClick={() => void onNewSession()}>新建</Button>}
        styles={{ body: { padding: 0, maxHeight: '70vh', overflow: 'auto' } }}
      >
        <Spin spinning={loadingSessions}>
          {sessions.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无会话" style={{ padding: 24 }} />
          ) : (
            <List
              dataSource={sessions}
              renderItem={(s) => (
                <List.Item
                  style={{
                    padding: '10px 12px',
                    cursor: 'pointer',
                    background: s.id === sessionId ? '#e6f4ff' : undefined,
                  }}
                  onClick={() => { if (s.id !== sessionId) setSessionId(s.id) }}
                  actions={[
                    <Button
                      key="del"
                      type="text"
                      size="small"
                      danger
                      icon={<DeleteOutlined />}
                      onClick={(e) => { e.stopPropagation(); void onDelete(s.id) }}
                    />,
                  ]}
                >
                  <Typography.Text ellipsis style={{ maxWidth: 160 }}>{s.title || s.id.slice(0, 8)}</Typography.Text>
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Card>

      <Card
        title="山东师范大学 · 知识库对话"
        styles={{ body: { display: 'flex', flexDirection: 'column', height: '70vh' } }}
      >
        <div style={{ flex: 1, overflow: 'auto', marginBottom: 12 }}>
          <Spin spinning={loadingHistory}>
            {messages.length === 0 && !loadingHistory && (
              <Empty
              style={{ marginTop: 80 }}
              description={
                <span>
                  问问山东师范大学：校训、宿舍食堂、招生政策、科研平台…
                  <br />
                  <Typography.Text type="secondary">弘德明志，博学笃行</Typography.Text>
                </span>
              }
            />
            )}
            {messages.map((m) => (
              <div key={m.id} style={{ marginBottom: 16, display: 'flex', justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start' }}>
                <div style={{
                  maxWidth: '80%',
                  background: m.role === 'user' ? token.colorPrimary : '#f5f5f5',
                  color: m.role === 'user' ? '#fff' : 'inherit',
                  padding: '10px 14px',
                  borderRadius: 12,
                  whiteSpace: 'pre-wrap',
                }}>
                  {m.content || (sending && m.role === 'assistant' ? '…' : '')}
                  {!!m.citations?.length && (
                    <Collapse
                      size="small"
                      style={{ marginTop: 8, background: '#fff', color: '#000' }}
                      items={[{
                        key: 'c',
                        label: '引用 (' + m.citations.length + ')',
                        children: (
                          <Space direction="vertical" style={{ width: '100%' }}>
                            {m.citations.map((c, i) => (
                              <Typography.Paragraph key={i} style={{ marginBottom: 0 }}>
                                <Typography.Text strong>{c.filename || c.document_id || 'doc'}</Typography.Text>
                                {c.score != null && <Typography.Text type="secondary"> · score {c.score.toFixed(3)}</Typography.Text>}
                                <br />
                                <Typography.Text type="secondary">{c.text}</Typography.Text>
                              </Typography.Paragraph>
                            ))}
                          </Space>
                        ),
                      }]}
                    />
                  )}
                </div>
              </div>
            ))}
            <div ref={bottomRef} />
          </Spin>
        </div>
        <Space.Compact style={{ width: '100%' }}>
          <Input.TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            autoSize={{ minRows: 1, maxRows: 4 }}
            placeholder="输入问题，Enter 发送"
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                void onSend()
              }
            }}
            disabled={sending}
          />
          <Button type="primary" icon={<SendOutlined />} loading={sending} onClick={() => void onSend()}>
            发送
          </Button>
        </Space.Compact>
      </Card>
    </div>
  )
}
