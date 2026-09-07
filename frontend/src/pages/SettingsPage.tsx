import { Card, Space, Typography, theme } from 'antd'
import { CheckOutlined } from '@ant-design/icons'
import { ACCENT_PRESETS, useThemeAccent } from '../theme/ThemeContext'

export default function SettingsPage() {
  const { accent, setAccent } = useThemeAccent()
  const { token } = theme.useToken()

  return (
    <Card title="外观设置">
      <Typography.Paragraph type="secondary">
        默认白底。强调色只作用于按钮、链接、菜单选中态等交互元素，不会改正文或页面背景。
      </Typography.Paragraph>
      <Typography.Text strong style={{ display: 'block', marginBottom: 12 }}>强调色</Typography.Text>
      <Space wrap size={12}>
        {ACCENT_PRESETS.map((p) => {
          const selected = accent.toLowerCase() === p.value.toLowerCase()
          return (
            <button
              key={p.value}
              type="button"
              title={p.label}
              onClick={() => setAccent(p.value)}
              style={{
                width: 40,
                height: 40,
                borderRadius: 10,
                border: selected ? `2px solid ${token.colorText}` : '2px solid #f0f0f0',
                background: p.value,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                boxShadow: selected ? `0 0 0 2px ${token.colorBgContainer}` : undefined,
              }}
            >
              {selected ? <CheckOutlined /> : null}
            </button>
          )
        })}
      </Space>
      <Typography.Paragraph style={{ marginTop: 16 }} type="secondary">
        当前：{ACCENT_PRESETS.find((p) => p.value.toLowerCase() === accent.toLowerCase())?.label || accent}
        （刷新后保留）
      </Typography.Paragraph>
    </Card>
  )
}
