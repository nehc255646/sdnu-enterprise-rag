import { useEffect, useState } from 'react'
import { Card, Space, Typography, theme, Form, Input, Button, Descriptions, Tag, message, Divider } from 'antd'
import { CheckOutlined, ReloadOutlined } from '@ant-design/icons'
import { ACCENT_PRESETS, useThemeAccent } from '../theme/ThemeContext'
import { fetchHealth, updateLlmConfig, type HealthResponse } from '../api/health'
import { useAuth } from '../auth/AuthContext'

export default function SettingsPage() {
  const { accent, setAccent } = useThemeAccent()
  const { token } = theme.useToken()
  const { auth } = useAuth()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loadingHealth, setLoadingHealth] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  async function loadHealth() {
    setLoadingHealth(true)
    try {
      const h = await fetchHealth()
      setHealth(h)
      form.setFieldsValue({
        base_url: h.llm_base_url || 'http://127.0.0.1:11434/v1',
        model: h.llm_model || '',
        api_key: '',
      })
    } catch (e) {
      message.error(e instanceof Error ? e.message : 'health 拉取失败')
    } finally {
      setLoadingHealth(false)
    }
  }

  useEffect(() => { void loadHealth() }, [])

  async function onSaveLlm(v: { base_url: string; model: string; api_key?: string }) {
    setSaving(true)
    try {
      await updateLlmConfig(
        { base_url: v.base_url, model: v.model, api_key: v.api_key || 'sk-no-auth' },
        auth?.access_token,
        auth?.tenant_id,
      )
      message.success('已切换主模型，正在刷新 health')
      await loadHealth()
    } catch (e) {
      if (e instanceof Error && e.message === 'LLM_CONFIG_API_MISSING') {
        message.warning('后端暂无 PUT /api/v1/llm/config，当前只能改 env 后重启 :8002；表单已就绪，接口一到即可切')
      } else {
        message.error(e instanceof Error ? e.message : '保存失败')
      }
    } finally {
      setSaving(false)
    }
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
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
      </Card>

      <Card
        title="主模型（OpenAI 兼容）"
        extra={<Button icon={<ReloadOutlined />} loading={loadingHealth} onClick={() => void loadHealth()}>刷新 health</Button>}
      >
        <Typography.Paragraph type="secondary">
          对齐 Nehchat / Neharness：`base_url` + `api_key` + `model`。本地 Ollama 可用 `http://127.0.0.1:11434/v1`，无鉴权填 `sk-no-auth`。
        </Typography.Paragraph>

        <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
          <Descriptions.Item label="health">
            {health ? <Tag color={health.status === 'ok' ? 'success' : 'warning'}>{health.status}</Tag> : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="llm_base_url">{health?.llm_base_url || '-'}</Descriptions.Item>
          <Descriptions.Item label="llm_model">{health?.llm_model || '-'}</Descriptions.Item>
          <Descriptions.Item label="embedding">
            {(health?.embedding_provider || '-') + ' / ' + (health?.embedding_model || '-')}
          </Descriptions.Item>
          <Descriptions.Item label="retrieval">{health?.retrieval_backend || '-'}</Descriptions.Item>
        </Descriptions>

        <Divider />

        <Form form={form} layout="vertical" onFinish={(v) => void onSaveLlm(v)}>
          <Form.Item name="base_url" label="OPENAI_BASE_URL / base_url" rules={[{ required: true }]}>
            <Input placeholder="http://127.0.0.1:11434/v1" />
          </Form.Item>
          <Form.Item name="api_key" label="OPENAI_API_KEY / api_key" extra="留空保存时按 sk-no-auth 提交（本地 Ollama）">
            <Input.Password placeholder="sk-no-auth 或云端 key" />
          </Form.Item>
          <Form.Item name="model" label="OPENAI_MODEL / model" rules={[{ required: true }]}>
            <Input placeholder="qwen2.5:3b" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={saving}>应用并刷新 health</Button>
        </Form>
      </Card>
    </Space>
  )
}
