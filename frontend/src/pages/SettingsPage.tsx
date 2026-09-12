import { useEffect, useState } from 'react'
import { Card, Space, Typography, theme, Form, Input, Button, Descriptions, Tag, message, Divider } from 'antd'
import { CheckOutlined, ReloadOutlined } from '@ant-design/icons'
import { ACCENT_PRESETS, useThemeAccent } from '../theme/ThemeContext'
import {
  fetchHealth,
  fetchLlmConfig,
  updateLlmConfig,
  type HealthResponse,
  type LlmConfigResponse,
} from '../api/health'

export default function SettingsPage() {
  const { accent, setAccent } = useThemeAccent()
  const { token } = theme.useToken()
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [llm, setLlm] = useState<LlmConfigResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form] = Form.useForm()

  async function refresh() {
    setLoading(true)
    try {
      const [h, c] = await Promise.all([fetchHealth(), fetchLlmConfig()])
      setHealth(h)
      setLlm(c)
      form.setFieldsValue({
        base_url: c.base_url || 'http://127.0.0.1:11434/v1',
        model: c.model || '',
        api_key: undefined,
      })
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载配置失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void refresh() }, [])

  async function onSaveLlm(v: { base_url: string; model: string; api_key?: string }, clearKey = false) {
    setSaving(true)
    try {
      const payload: { base_url: string; model: string; api_key?: string } = {
        base_url: v.base_url,
        model: v.model,
      }
      if (clearKey) {
        payload.api_key = ''
      } else if (typeof v.api_key === 'string' && v.api_key.length > 0) {
        payload.api_key = v.api_key
      }
      const updated = await updateLlmConfig(payload)
      setLlm(updated)
      message.success('主模型已切换')
      const h = await fetchHealth()
      setHealth(h)
      form.setFieldValue('api_key', undefined)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      <Card className="surface-card" title="外观设置">
        <Typography.Paragraph type="secondary">
          暖色纸感底。强调色作用于按钮、链接、菜单选中态与对话气泡，不改正文纸色。
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
        className="surface-card"
        title="主模型（OpenAI 兼容）"
        extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={() => void refresh()}>刷新</Button>}
      >
        <Typography.Paragraph type="secondary">
          OpenAI 兼容接口：`base_url` / `api_key` / `model`。`api_key` 留空不提交=保持原值；提交空串=清成 `sk-no-auth`。私网 / Docker 服务名不可作为 base_url。
        </Typography.Paragraph>

        <Descriptions size="small" column={1} bordered style={{ marginBottom: 16 }}>
          <Descriptions.Item label="health">
            {health ? <Tag color={health.status === 'ok' ? 'success' : 'warning'}>{health.status}</Tag> : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="llm_base_url">{llm?.base_url || '-'}</Descriptions.Item>
          <Descriptions.Item label="llm_model">{llm?.model || '-'}</Descriptions.Item>
          <Descriptions.Item label="api_key_set">
            {llm ? (llm.api_key_set ? <Tag color="blue">已设置</Tag> : <Tag>sk-no-auth / 空</Tag>) : '-'}
          </Descriptions.Item>
          <Descriptions.Item label="embedding">
            {(health?.embedding_provider || '-') + ' / ' + (health?.embedding_model || '-')}
          </Descriptions.Item>
          <Descriptions.Item label="retrieval">{health?.retrieval_backend || '-'}</Descriptions.Item>
        </Descriptions>

        <Divider />

        <Form
          form={form}
          layout="vertical"
          onFinish={(v) => void onSaveLlm(v)}
          initialValues={{ base_url: 'http://127.0.0.1:11434/v1' }}
        >
          <Form.Item name="base_url" label="base_url" rules={[{ required: true }]}>
            <Input placeholder="http://127.0.0.1:11434/v1" />
          </Form.Item>
          <Form.Item
            name="api_key"
            label="api_key"
            extra="不填则保持服务端原值；填空并保存则清成 sk-no-auth"
          >
            <Input.Password placeholder="不修改请留空" visibilityToggle />
          </Form.Item>
          <Form.Item name="model" label="model" rules={[{ required: true }]}>
            <Input placeholder="qwen2.5:3b" />
          </Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" loading={saving}>应用配置</Button>
            <Button
              loading={saving}
              onClick={() => {
                const v = form.getFieldsValue()
                void onSaveLlm(v, true)
              }}
            >
              清除 key 为 sk-no-auth
            </Button>
          </Space>
        </Form>
      </Card>
    </Space>
  )
}
