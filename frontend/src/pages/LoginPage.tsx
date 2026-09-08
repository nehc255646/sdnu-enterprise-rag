import { useState } from 'react'
import { Button, Card, Form, Input, Tabs, Typography, message, Space } from 'antd'
import { useNavigate } from 'react-router-dom'
import { login, register } from '../api/auth'
import { useAuth } from '../auth/AuthContext'

const defaultTenant = (import.meta.env.VITE_DEFAULT_TENANT as string) || 'sdnu-demo'

export default function LoginPage() {
  const [loading, setLoading] = useState(false)
  const { setAuth } = useAuth()
  const nav = useNavigate()

  async function onLogin(v: { email: string; password: string; tenant_id: string }) {
    setLoading(true)
    try {
      const auth = await login(v.email, v.password, v.tenant_id)
      setAuth(auth)
      message.success('登录成功')
      nav('/chat')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '登录失败')
    } finally {
      setLoading(false)
    }
  }

  async function onRegister(v: { email: string; password: string; tenant_id?: string }) {
    setLoading(true)
    try {
      const auth = await register(v.email, v.password, v.tenant_id || defaultTenant)
      setAuth(auth)
      message.success('注册成功')
      nav('/chat')
    } catch (e) {
      message.error(e instanceof Error ? e.message : '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: '#ffffff' }}>
      <Card style={{ width: 440 }}>
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <img src="/sdnu-emblem-128.png" alt="山东师范大学校徽" width={72} height={72} />
          <Typography.Title level={4} style={{ margin: '12px 0 4px' }}>
            山东师范大学知识库
          </Typography.Title>
          <Typography.Text type="secondary">弘德明志，博学笃行</Typography.Text>
        </div>
        <Typography.Paragraph type="secondary" style={{ textAlign: 'center' }}>
          Demo 租户建议使用 <Typography.Text code>{defaultTenant}</Typography.Text>
        </Typography.Paragraph>
        <Tabs
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form layout="vertical" onFinish={onLogin} initialValues={{ tenant_id: defaultTenant }}>
                  <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
                    <Input placeholder="you@example.com" />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
                    <Input.Password />
                  </Form.Item>
                  <Form.Item name="tenant_id" label="租户 ID" rules={[{ required: true }]}>
                    <Input />
                  </Form.Item>
                  <Button type="primary" htmlType="submit" block loading={loading}>登录</Button>
                </Form>
              ),
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form layout="vertical" onFinish={onRegister} initialValues={{ tenant_id: defaultTenant }}>
                  <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
                    <Input />
                  </Form.Item>
                  <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
                    <Input.Password />
                  </Form.Item>
                  <Form.Item name="tenant_id" label="租户 ID">
                    <Input placeholder={defaultTenant} />
                  </Form.Item>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Button type="primary" htmlType="submit" block loading={loading}>注册并进入</Button>
                  </Space>
                </Form>
              ),
            },
          ]}
        />
      </Card>
    </div>
  )
}
