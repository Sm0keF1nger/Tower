import { useState } from 'react'
import {
  BarChartOutlined,
  DashboardOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  LineChartOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Avatar, Button, Dropdown, Layout, Menu, Space, Tag, Typography } from 'antd'
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Analytics from './pages/Analytics'
import Dashboard from './pages/Dashboard'
import DataManagement from './pages/DataManagement'
import Forecast from './pages/Forecast'
import ModelPerformance from './pages/ModelPerformance'
import Login from './pages/Login'
import AuthCallback from './pages/AuthCallback'
import ProtectedRoute from './components/ProtectedRoute'
import { useAuth } from './context/AuthContext'

const { Header, Sider, Content } = Layout

function AppLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()
  const { user, isAdmin, logout } = useAuth()

  const menuItems = [
    { key: '/', icon: <DashboardOutlined />, label: <Link to="/">Панель</Link> },
    { key: '/analytics', icon: <BarChartOutlined />, label: <Link to="/analytics">Аналітика</Link> },
    { key: '/forecast', icon: <LineChartOutlined />, label: <Link to="/forecast">Прогноз</Link> },
    ...(isAdmin ? [
      { key: '/data', icon: <DatabaseOutlined />, label: <Link to="/data">Дані</Link> },
      { key: '/model', icon: <ExperimentOutlined />, label: <Link to="/model">Моделі</Link> },
    ] : []),
  ]

  const userMenu = {
    items: [
      { key: 'role', disabled: true, label: `Роль: ${isAdmin ? 'Адміністратор' : 'Менеджер'}` },
      { type: 'divider' as const },
      { key: 'logout', icon: <LogoutOutlined />, label: 'Вийти', onClick: logout },
    ],
  }

  return (
    <Layout className="app-shell">
      <Sider collapsible collapsed={collapsed} trigger={null} width={240} className="sidebar">
        <div className="brand">
          <div className="brand-mark">T</div>
          {!collapsed && (
            <div>
              <Typography.Text className="brand-title">Tower</Typography.Text>
              <div className="brand-subtitle">Аналітика клініки</div>
            </div>
          )}
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[location.pathname]} items={menuItems} />
      </Sider>
      <Layout>
        <Header className="topbar">
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed((value) => !value)}
          />
          <Typography.Text type="secondary" className="topbar-title">Аналіз і прогнозування навантаження клініки</Typography.Text>
          <div className="topbar-spacer" />
          <Tag color={isAdmin ? 'blue' : 'green'}>{isAdmin ? 'Адміністратор' : 'Менеджер'}</Tag>
          <Dropdown menu={userMenu} placement="bottomRight">
            <Space className="user-menu-trigger">
              <Avatar icon={<UserOutlined />} />
              <Typography.Text>{user?.display_name ?? user?.username}</Typography.Text>
            </Space>
          </Dropdown>
        </Header>
        <Content className="content">
          <Routes>
            <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
            <Route path="/analytics" element={<ProtectedRoute><Analytics /></ProtectedRoute>} />
            <Route path="/forecast" element={<ProtectedRoute><Forecast /></ProtectedRoute>} />
            <Route path="/data" element={<ProtectedRoute adminOnly><DataManagement /></ProtectedRoute>} />
            <Route path="/model" element={<ProtectedRoute adminOnly><ModelPerformance /></ProtectedRoute>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  )
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/*" element={<AppLayout />} />
    </Routes>
  )
}
