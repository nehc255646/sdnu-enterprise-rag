import { Layout, Menu, Typography, Button, Space, Tag } from 'antd'
import { FileTextOutlined, MessageOutlined, LogoutOutlined } from '@ant-design/icons'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const { Header, Sider, Content } = Layout

export default function AppLayout() {
  const loc = useLocation()
  const nav = useNavigate()
  const { auth, logout } = useAuth()
  const key = loc.pathname.startsWith('/docs') ? 'docs' : 'chat'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={64} theme="light" style={{ borderRight: '1px solid #f0f0f0' }}>
        <div style={{ padding: 16, fontWeight: 700 }}>山师大 RAG</div>
        <Menu
          mode="inline"
          selectedKeys={[key]}
          items={[
            { key: 'chat', icon: <MessageOutlined />, label: <Link to="/chat">知识库对话</Link> },
            { key: 'docs', icon: <FileTextOutlined />, label: <Link to="/docs">文档管理</Link> },
          ]}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', borderBottom: '1px solid #f0f0f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingInline: 24 }}>
          <Typography.Text type="secondary">知识库问答 Demo</Typography.Text>
          <Space>
            {auth?.tenant_id && <Tag color="blue">{auth.tenant_id}</Tag>}
            <Typography.Text>{auth?.email || auth?.user_id}</Typography.Text>
            <Button icon={<LogoutOutlined />} onClick={() => { logout(); nav('/login') }}>退出</Button>
          </Space>
        </Header>
        <Content style={{ padding: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
