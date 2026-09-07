export type TokenResponse = {
  access_token: string
  token_type: string
  tenant_id: string
  user_id: string
}

export type DocumentListItem = {
  document_id: string
  tenant_id: string
  filename: string
  doc_type: string
  status: string
  chunk_count: number
  error_message?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type DocumentListResponse = {
  tenant_id: string
  total: number
  items: DocumentListItem[]
}

export type Citation = {
  document_id?: string | null
  filename?: string | null
  chunk_index?: number | null
  score?: number | null
  text: string
  point_id?: string | null
  doc_type?: string | null
}

export type SessionOut = {
  id: string
  tenant_id: string
  user_id: string
  title?: string | null
  created_at?: string | null
  updated_at?: string | null
}

export type MessageOut = {
  id: string
  role: string
  content: string
  citations_json?: string | null
  created_at?: string | null
}

export type SessionWithMessages = SessionOut & {
  messages: MessageOut[]
}
