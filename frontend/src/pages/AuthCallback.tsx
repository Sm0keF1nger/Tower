import { Alert, Spin, Typography } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function AuthCallback() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { reloadUser } = useAuth()
  const [error, setError] = useState('')
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true

    const complete = async () => {
      const code = params.get('code')
      const state = params.get('state')
      const expectedState = sessionStorage.getItem('tower_oauth_state')
      const verifier = sessionStorage.getItem('tower_pkce_verifier')
      const redirectUri = sessionStorage.getItem('tower_redirect_uri')
      const oauthError = params.get('error_description') ?? params.get('error')

      if (oauthError) throw new Error(oauthError)
      if (!code || !state || !verifier || !redirectUri || state !== expectedState) {
        throw new Error('Не вдалося перевірити OAuth-відповідь. Спробуйте увійти повторно.')
      }

      await authApi.exchange(code, verifier, redirectUri)
      sessionStorage.removeItem('tower_oauth_state')
      sessionStorage.removeItem('tower_pkce_verifier')
      sessionStorage.removeItem('tower_redirect_uri')
      await reloadUser()
      navigate('/', { replace: true })
    }

    complete().catch((err: Error) => setError(err.message))
  }, [params, navigate, reloadUser])

  return (
    <div className="login-page">
      {error ? (
        <Alert type="error" showIcon message="Авторизацію не завершено" description={error} />
      ) : (
        <div className="callback-state"><Spin size="large" /><Typography.Text>Завершуємо вхід…</Typography.Text></div>
      )}
    </div>
  )
}
