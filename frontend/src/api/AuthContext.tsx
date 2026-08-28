import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError } from './client'
import type { AuthMethod, SessionInfo } from './types'

type AuthStatus = 'loading' | 'signed-out' | 'mfa-pending' | 'signed-in'

interface AuthContextValue {
  status: AuthStatus
  session: SessionInfo | null
  authMethod: AuthMethod | 'loading'
  login: (username: string, password: string) => Promise<void>
  verifyMfa: (code: string) => Promise<void>
  logout: () => Promise<void>
  refreshSession: () => Promise<void>
  refreshAuthConfig: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [authMethod, setAuthMethod] = useState<AuthMethod | 'loading'>('loading')

  const refreshSession = useCallback(async () => {
    try {
      const info = await api.get<SessionInfo>('/api/auth/session')
      setSession(info)
      setStatus('signed-in')
    } catch {
      setSession(null)
      setStatus('signed-out')
    }
  }, [])

  const refreshAuthConfig = useCallback(async () => {
    const config = await api.get<{ auth_method: AuthMethod }>('/api/auth/config')
    setAuthMethod(config.auth_method)
  }, [])

  useEffect(() => {
    refreshSession()
    refreshAuthConfig()
  }, [refreshSession, refreshAuthConfig])

  const login = useCallback(async (username: string, password: string) => {
    const result = await api.post<{ mfa_required: boolean }>('/api/auth/login', { username, password })
    if (result.mfa_required) {
      setStatus('mfa-pending')
    } else {
      await refreshSession()
    }
  }, [refreshSession])

  const verifyMfa = useCallback(async (code: string) => {
    await api.post('/api/auth/mfa/verify', { code })
    await refreshSession()
  }, [refreshSession])

  const logout = useCallback(async () => {
    await api.post('/api/auth/logout')
    setSession(null)
    setStatus('signed-out')
  }, [])

  return (
    <AuthContext.Provider
      value={{ status, session, authMethod, login, verifyMfa, logout, refreshSession, refreshAuthConfig }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export { ApiError }
