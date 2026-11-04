import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, getToken, setToken, setUnauthorizedHandler, type Role } from './api'
import { takeActiveForLogout } from './tracking'

interface User { email: string; full_name: string; role: Role }
interface Ctx {
  user: User | null
  ready: boolean
  demo: boolean
  setDemo: (v: boolean) => void
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}
const AuthCtx = createContext<Ctx>(null!)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)
  const [demo, setDemo] = useState(false)

  const clear = useCallback(() => { setToken(null); setUser(null) }, [])

  useEffect(() => {
    setUnauthorizedHandler(clear)
    if (!getToken()) { setReady(true); return }
    api<User>('/auth/me').then(setUser).catch(clear).finally(() => setReady(true))
  }, [clear])

  const login = async (email: string, password: string) => {
    const t = await api<{ access_token: string }>('/auth/login', { json: { email, password } })
    setToken(t.access_token)
    setUser(await api<User>('/auth/me'))
  }

  const logout = async () => {
    const exit = takeActiveForLogout() // exit is recorded by the logout call itself
    try { await api('/auth/logout', { json: exit }) } catch { /* session may already be gone */ }
    clear()
  }

  return <AuthCtx.Provider value={{ user, ready, demo, setDemo, login, logout }}>{children}</AuthCtx.Provider>
}
