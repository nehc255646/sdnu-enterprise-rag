import { apiFetch, saveAuth, type StoredAuth } from './client'
import type { TokenResponse } from '../types'

export async function login(email: string, password: string, tenant_id: string) {
  const data = (await apiFetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password, tenant_id }),
  })) as TokenResponse
  const stored: StoredAuth = {
    access_token: data.access_token,
    tenant_id: data.tenant_id,
    user_id: data.user_id,
    email,
  }
  saveAuth(stored)
  return stored
}

export async function register(email: string, password: string, tenant_id?: string) {
  const data = (await apiFetch('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password, tenant_id: tenant_id || undefined }),
  })) as TokenResponse
  const stored: StoredAuth = {
    access_token: data.access_token,
    tenant_id: data.tenant_id,
    user_id: data.user_id,
    email,
  }
  saveAuth(stored)
  return stored
}
