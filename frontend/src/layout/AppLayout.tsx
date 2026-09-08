import { Layout, Menu, Typography, Button, Space, Tag } from 'antd'
import { FileTextOutlined, MessageOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const { Header, Sider, Content } = Layout

export default function AppLayout() {
  const loc = useLocation()
  const nav = useNavigate()
  const { auth, logout } = useAuth()
  const key = loc.pathname.startsWith('/docs')
    ? 'docs'
    : loc.pathname.startsWith('/settings')
      ? 'settings'
      : 'chat'

  return (
    <Layout style={{ minHeight: '100vh', background: '#ffffff' }}>
      <Sider breakpoint="lg" collapsedWidth={72} theme="light" style={{ borderRight: '1px solid #f0f0f0', background: '#ffffff' }}>
        <div style={{ padding: '16px 12px 8px', display: 'flex', alignItems: 'center', gap: 10 }}>
          <img src="/sdnu-emblem-64.png" alt="山东师范大学校徽" width={40} height={40} style={{ flexShrink: 0 }} />
          <div style={{ minWidth: 0, lineHeight: 1.25 }}>
            <div style={{ fontWeight: 700, fontSize: 14 }}>山东师范大学</div>
            <div style={{ fontSize: 12, color: 'rgba(0,0,0,0.45)' }}>知识库问答</div>
          </div>
        </div>
        <Typography.Paragraph
          type="secondary"
          style={{ margin: '0 12px 12px', fontSize: 12, lineHeight: 1.4 }}
        >
          弘德明志，博学笃行
        </Typography.Paragraph>
        <Menu
          mode="inline"
          selectedKeys={[key]}
          style={{ background: '#ffffff', borderInlineEnd: 'none' }}
          items={[
            { key: 'chat', icon: <MessageOutlined />, label: <Link to="/chat">知识库对话</Link> },
            { key: 'docs', icon: <FileTextOutlined />, label: <Link to="/docs">文档管理</Link> },
            { key: 'settings', icon: <SettingOutlined />, label: <Link to="/settings">设置</Link> },
          ]}
        />
      </Sider>
      <Layout style={{ background: '#ffffff' }}>
        <Header style={{ background: '#ffffff', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingInline: 24 }}>
          <Typography.Text type="secondary">了解山东师范大学 · 知识库问答</Typography.Text>
          <Space>
            {auth?.tenant_id && <Tag color="processing">{auth.tenant_id}</Tag>}
            <Typography.Text>{auth?.email || auth?.user_id}</Typography.Text>
            <Button icon={<LogoutOutlined />} onClick={() => { logout(); nav('/login') }}>退出</Button>
          </Space>
        </Header>
        <Content style={{ padding: 24, background: '#ffffff' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
