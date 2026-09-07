import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import { clearAuth, loadAuth, type StoredAuth } from '../api/client'

type AuthCtx = {
  auth: StoredAuth | null
  setAuth: (a: StoredAuth | null) => void
  logout: () => void
}

const Ctx = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuthState] = useState<StoredAuth | null>(() => loadAuth())
  const value = useMemo<AuthCtx>(() => ({
    auth,
    setAuth: (a) => setAuthState(a),
    logout: () => { clearAuth(); setAuthState(null) },
  }), [auth])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth() {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAuth outside provider')
  return v
}
