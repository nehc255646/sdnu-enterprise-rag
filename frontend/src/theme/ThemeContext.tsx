import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ConfigProvider, theme as antTheme } from 'antd'
import zhCN from 'antd/locale/zh_CN'

const STORAGE_KEY = 'sdnu_rag_accent'
export const DEFAULT_ACCENT = '#1677ff'

export const ACCENT_PRESETS = [
  { label: '默认蓝', value: '#1677ff' },
  { label: '青绿', value: '#13c2c2' },
  { label: '极光绿', value: '#52c41a' },
  { label: '日落橙', value: '#fa8c16' },
  { label: '洋红', value: '#eb2f96' },
  { label: '酱紫', value: '#722ed1' },
] as const

type ThemeCtx = {
  accent: string
  setAccent: (c: string) => void
}

const Ctx = createContext<ThemeCtx | null>(null)

function loadAccent(): string {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v && /^#[0-9a-fA-F]{6}$/.test(v)) return v
  } catch { /* ignore */ }
  return DEFAULT_ACCENT
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [accent, setAccentState] = useState(loadAccent)

  useEffect(() => {
    document.documentElement.style.setProperty('--accent', accent)
  }, [accent])

  const setAccent = (c: string) => {
    setAccentState(c)
    try { localStorage.setItem(STORAGE_KEY, c) } catch { /* ignore */ }
  }

  const value = useMemo(() => ({ accent, setAccent }), [accent])

  return (
    <Ctx.Provider value={value}>
      <ConfigProvider
        locale={zhCN}
        theme={{
          algorithm: antTheme.defaultAlgorithm,
          token: {
            colorPrimary: accent,
            colorLink: accent,
            colorInfo: accent,
            borderRadius: 8,
            colorBgBase: '#ffffff',
            colorTextBase: 'rgba(0,0,0,0.88)',
          },
        }}
      >
        {children}
      </ConfigProvider>
    </Ctx.Provider>
  )
}

export function useThemeAccent() {
  const v = useContext(Ctx)
  if (!v) throw new Error('useThemeAccent outside provider')
  return v
}
