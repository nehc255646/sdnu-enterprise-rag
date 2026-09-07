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
      <Sider breakpoint="lg" collapsedWidth={64} theme="light" style={{ borderRight: '1px solid #f0f0f0', background: '#ffffff' }}>
        <div style={{ padding: 16, fontWeight: 700 }}>山师大 RAG</div>
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
          <Typography.Text type="secondary">知识库问答 Demo</Typography.Text>
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
