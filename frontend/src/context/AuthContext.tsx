import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { authApi } from '../services/api'
import { getAccessToken } from '../services/authStorage'
import type { CurrentUser } from '../types/api'

interface AuthContextValue {
  user: CurrentUser | null
  loading: boolean
  isAdmin: boolean
  login: () => Promise<void>
  reloadUser: () => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

function base64Url(bytes: Uint8Array): string {
  let binary = ''
  bytes.forEach((byte) => { binary += String.fromCharCode(byte) })
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

async function createPkce(): Promise<{ verifier: string; challenge: string }> {
  const bytes = new Uint8Array(64)
  crypto.getRandomValues(bytes)
  const verifier = base64Url(bytes)
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))
  return { verifier, challenge: base64Url(new Uint8Array(digest)) }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(true)

  const reloadUser = useCallback(async () => {
    try {
      setUser(await authApi.me())
    } catch {
      const refreshed = await authApi.tryRefresh()
      if (refreshed) setUser(await authApi.me())
      else setUser(null)
    }
  }, [])

  useEffect(() => {
    const restore = async () => {
      if (!getAccessToken()) {
        const refreshed = await authApi.tryRefresh()
        if (!refreshed) {
          setLoading(false)
          return
        }
      }
      try { setUser(await authApi.me()) } catch { setUser(null) }
      finally { setLoading(false) }
    }
    restore()
  }, [])

  const login = useCallback(async () => {
    const config = await authApi.config()
    const { verifier, challenge } = await createPkce()
    const stateBytes = new Uint8Array(24)
    crypto.getRandomValues(stateBytes)
    const state = base64Url(stateBytes)
    sessionStorage.setItem('tower_pkce_verifier', verifier)
    sessionStorage.setItem('tower_oauth_state', state)
    sessionStorage.setItem('tower_redirect_uri', config.redirect_uri)

    const params = new URLSearchParams({
      client_id: config.client_id,
      redirect_uri: config.redirect_uri,
      response_type: 'code',
      scope: config.scope,
      code_challenge: challenge,
      code_challenge_method: 'S256',
      state,
    })
    window.location.assign(`${config.authorization_endpoint}?${params.toString()}`)
  }, [])

  const logout = useCallback(async () => {
    await authApi.logout()
    setUser(null)
  }, [])

  const value = useMemo(() => ({
    user,
    loading,
    isAdmin: user?.roles.includes('admin') ?? false,
    login,
    reloadUser,
    logout,
  }), [user, loading, login, reloadUser, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider відсутній')
  return value
}
