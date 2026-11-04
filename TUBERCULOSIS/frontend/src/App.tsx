import type { ReactNode } from 'react'
import { Navigate, NavLink, Outlet, Route, Routes } from 'react-router-dom'
import type { Role } from './api'
import { useAuth } from './auth'
import Login from './pages/Login'
import Cases from './pages/Cases'
import CaseDetail from './pages/CaseDetail'
import Dashboard from './pages/Dashboard'
import Audit from './pages/Audit'

const NAV: { to: string; label: string; roles: Role[] }[] = [
  { to: '/cases', label: 'Cases', roles: ['admin', 'operator', 'reviewer', 'auditor'] },
  { to: '/dashboard', label: 'Dashboard', roles: ['admin', 'operator', 'reviewer', 'auditor'] },
  { to: '/audit', label: 'Audit log', roles: ['admin', 'auditor'] },
]

function Guard({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (!roles.includes(user.role)) return <p className="error">Your role is not authorized for this module.</p>
  return <>{children}</>
}

function Layout() {
  const { user, logout, demo } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  return (
    <>
      {demo && <div className="demo-banner">DEMO MODE: results come from a demonstration engine, not a validated model.</div>}
      <header className="topbar">
        <strong>SP-02 TB screening</strong>
        <nav>
          {NAV.filter((n) => n.roles.includes(user.role)).map((n) => (
            <NavLink key={n.to} to={n.to}>{n.label}</NavLink>
          ))}
        </nav>
        <span className="spacer" />
        <span>{user.full_name} ({user.role})</span>
        <button onClick={logout}>Log out</button>
      </header>
      <main><Outlet /></main>
      <footer>Decision-support research prototype. Not a diagnostic device.</footer>
    </>
  )
}

export default function App() {
  const { ready } = useAuth()
  if (!ready) return <p>Loading...</p>
  const all: Role[] = ['admin', 'operator', 'reviewer', 'auditor']
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Layout />}>
        <Route path="/cases" element={<Guard roles={all}><Cases /></Guard>} />
        <Route path="/cases/:id" element={<Guard roles={all}><CaseDetail /></Guard>} />
        <Route path="/dashboard" element={<Guard roles={all}><Dashboard /></Guard>} />
        <Route path="/audit" element={<Guard roles={['admin', 'auditor']}><Audit /></Guard>} />
        <Route path="*" element={<Navigate to="/cases" replace />} />
      </Route>
    </Routes>
  )
}
