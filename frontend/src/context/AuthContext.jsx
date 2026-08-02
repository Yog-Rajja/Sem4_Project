import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import api from '../lib/api'
import {
  clearSession,
  getAccessToken,
  getStoredUser,
  storeTokens,
  storeUser,
} from '../lib/auth'

const AuthContext = createContext(null)

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(getStoredUser)
  // `booting` covers the first render, while we confirm a stored token is still
  // valid. Routes wait on it so a refresh never flashes the login screen.
  const [booting, setBooting] = useState(Boolean(getAccessToken()))

  useEffect(() => {
    if (!getAccessToken()) {
      setBooting(false)
      return
    }
    let cancelled = false
    api
      .get('/auth/me/')
      .then(({ data }) => {
        if (cancelled) return
        setUser(data)
        storeUser(data)
      })
      .catch(() => {
        if (cancelled) return
        clearSession()
        setUser(null)
      })
      .finally(() => !cancelled && setBooting(false))
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async ({ username, password }) => {
    const { data } = await api.post('/auth/login/', { username, password })
    storeTokens(data)
    const me = await api.get('/auth/me/')
    setUser(me.data)
    storeUser(me.data)
    return me.data
  }, [])

  const register = useCallback(async (payload) => {
    const { data } = await api.post('/auth/register/', payload)
    storeTokens(data)
    setUser(data.user)
    storeUser(data.user)
    return data.user
  }, [])

  const logout = useCallback(() => {
    clearSession()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, booting, login, register, logout, isAuthenticated: Boolean(user) }),
    [user, booting, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
