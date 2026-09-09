import { useState } from 'react'
import { Button, Card, Form, Input, Tabs, Typography, message } from 'antd'
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
    <div className="login-shell">
      <aside className="login-brand">
        <img className="login-brand-art" src="/login-art.jpg" alt="" />
        <div className="login-brand-scrim" />
        <div className="login-brand-inner">
          <img src="/sdnu-emblem-128.png" alt="山东师范大学校徽" width={72} height={72} />
          <h1>山东师范大学</h1>
          <p className="login-motto">弘德明志 · 博学笃行</p>
          <p className="login-en">Shandong Normal University · Knowledge Base</p>
          <ul className="login-points">
            <li>多租户知识库检索与引用溯源</li>
            <li>流式对话，校史校情即问即答</li>
            <li>文档入库、会话与模型热切换</li>
          </ul>
        </div>
      </aside>
      <main className="login-panel">
        <Card className="login-card" variant="borderless">
          <div className="login-card-head">
            <Typography.Title level={3} style={{ margin: 0 }}>欢迎回来</Typography.Title>
            <Typography.Paragraph type="secondary" style={{ margin: '8px 0 0' }}>
              Demo 租户建议使用 <Typography.Text code>{defaultTenant}</Typography.Text>
            </Typography.Paragraph>
          </div>
          <Tabs
            items={[
              {
                key: 'login',
                label: '登录',
                children: (
                  <Form layout="vertical" onFinish={onLogin} initialValues={{ tenant_id: defaultTenant }}>
                    <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
                      <Input size="large" placeholder="you@example.com" />
                    </Form.Item>
                    <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
                      <Input.Password size="large" />
                    </Form.Item>
                    <Form.Item name="tenant_id" label="租户 ID" rules={[{ required: true }]}>
                      <Input size="large" />
                    </Form.Item>
                    <Button type="primary" htmlType="submit" block size="large" loading={loading}>登录</Button>
                  </Form>
                ),
              },
              {
                key: 'register',
                label: '注册',
                children: (
                  <Form layout="vertical" onFinish={onRegister} initialValues={{ tenant_id: defaultTenant }}>
                    <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
                      <Input size="large" />
                    </Form.Item>
                    <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
                      <Input.Password size="large" />
                    </Form.Item>
                    <Form.Item name="tenant_id" label="租户 ID">
                      <Input size="large" placeholder={defaultTenant} />
                    </Form.Item>
                    <Button type="primary" htmlType="submit" block size="large" loading={loading}>注册并进入</Button>
                  </Form>
                ),
              },
            ]}
          />
        </Card>
      </main>
    </div>
  )
}
