import { Alert, Button, Card, Spin, Typography } from 'antd'
import { LoginOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const { user, loading, login } = useAuth()
  const [error, setError] = useState('')
  const [starting, setStarting] = useState(false)

  if (loading) return <div className="login-page"><Spin size="large" /></div>
  if (user) return <Navigate to="/" replace />

  const handleLogin = async () => {
    setStarting(true)
    setError('')
    try { await login() }
    catch (err) { setError(err instanceof Error ? err.message : 'Не вдалося почати авторизацію.') }
    finally { setStarting(false) }
  }

  return (
    <div className="login-page">
      <Card className="login-card" bordered={false}>
        <div className="login-brand-mark">T</div>
        <Typography.Title level={2}>Tower</Typography.Title>
        <Typography.Paragraph type="secondary">
          Cистема аналізу та прогнозування навантаження клініки.
        </Typography.Paragraph>
        {error && <Alert type="error" showIcon message="Помилка авторизації" description={error} style={{ marginBottom: 16 }} />}
        <Button type="primary" size="large" block icon={<LoginOutlined />} loading={starting} onClick={handleLogin}>
          Увійти
        </Button>
      </Card>
    </div>
  )
}
