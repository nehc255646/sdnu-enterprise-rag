import { useState } from 'react'
import { Layout, Menu, Typography, Button, Tag } from 'antd'
import { FileTextOutlined, MessageOutlined, LogoutOutlined, SettingOutlined } from '@ant-design/icons'
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

const { Header, Sider, Content } = Layout

const TITLES: Record<string, { kicker: string; title: string }> = {
  chat: { kicker: 'Knowledge', title: '知识库对话' },
  docs: { kicker: 'Corpus', title: '文档管理' },
  settings: { kicker: 'System', title: '设置' },
}

export default function AppLayout() {
  const loc = useLocation()
  const nav = useNavigate()
  const { auth, logout } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const key = loc.pathname.startsWith('/docs')
    ? 'docs'
    : loc.pathname.startsWith('/settings')
      ? 'settings'
      : 'chat'
  const heading = TITLES[key]
  const initial = (auth?.email || auth?.user_id || 'U').slice(0, 1).toUpperCase()

  return (
    <Layout className="app-shell">
      <Sider
        className="app-sider"
        breakpoint="lg"
        collapsedWidth={72}
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        width={232}
      >
        <div className={'brand-lockup' + (collapsed ? ' is-collapsed' : '')}>
          <img src="/sdnu-emblem-64.png" alt="山东师范大学校徽" width={40} height={40} />
          {!collapsed && (
            <div style={{ minWidth: 0 }}>
              <div className="brand-name">山东师范大学</div>
              <div className="brand-sub">知识库问答</div>
            </div>
          )}
        </div>
        {!collapsed && <p className="brand-motto">弘德明志 · 博学笃行</p>}
        <Menu
          className="app-menu"
          mode="inline"
          selectedKeys={[key]}
          items={[
            { key: 'chat', icon: <MessageOutlined />, label: <Link to="/chat">知识库对话</Link> },
            { key: 'docs', icon: <FileTextOutlined />, label: <Link to="/docs">文档管理</Link> },
            { key: 'settings', icon: <SettingOutlined />, label: <Link to="/settings">设置</Link> },
          ]}
        />
      </Sider>
      <Layout>
        <Header className="app-header">
          <div>
            <div className="header-kicker">{heading.kicker}</div>
            <div className="header-title">{heading.title}</div>
          </div>
          <div className="header-user">
            {auth?.tenant_id && <Tag color="red">{auth.tenant_id}</Tag>}
            <div className="user-chip">
              <span className="user-avatar">{initial}</span>
              <span className="user-email">
                <Typography.Text style={{ maxWidth: 180 }} ellipsis>
                  {auth?.email || auth?.user_id}
                </Typography.Text>
              </span>
            </div>
            <Button
              className="logout-btn"
              icon={<LogoutOutlined />}
              onClick={() => { logout(); nav('/login') }}
            >
              <span className="logout-label">退出</span>
            </Button>
          </div>
        </Header>
        <Content className="app-content">
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
