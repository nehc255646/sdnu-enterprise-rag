import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ConfigProvider, theme as antTheme } from 'antd'
import zhCN from 'antd/locale/zh_CN'

const STORAGE_KEY = 'sdnu_rag_accent'
/** SDNU school red (approx. from official brand guide) */
export const DEFAULT_ACCENT = '#E60012'

export const ACCENT_PRESETS = [
  { label: '校红', value: '#E60012' },
  { label: '校蓝', value: '#1B4F8A' },
  { label: '默认蓝', value: '#1677ff' },
  { label: '青绿', value: '#13c2c2' },
  { label: '极光绿', value: '#52c41a' },
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

const FONT = `'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif`

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
            borderRadius: 12,
            colorBgBase: '#fffdf9',
            colorBgLayout: '#f3efe8',
            colorTextBase: '#1c1917',
            colorBorder: 'rgba(28,25,23,0.10)',
            colorBorderSecondary: 'rgba(28,25,23,0.06)',
            fontFamily: FONT,
            fontSize: 14,
            controlHeight: 36,
          },
          components: {
            Layout: {
              headerBg: 'transparent',
              bodyBg: 'transparent',
              siderBg: 'transparent',
            },
            Card: {
              headerFontSize: 16,
            },
            Menu: {
              itemBorderRadius: 10,
              itemMarginInline: 0,
            },
            Button: {
              fontWeight: 560,
            },
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
