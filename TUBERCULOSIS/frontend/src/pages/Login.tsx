import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { user, login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  if (user) return <Navigate to="/cases" replace />

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try { await login(email, password); nav('/cases') } catch (err) { setError((err as Error).message) }
  }

  return (
    <form className="card login" onSubmit={submit}>
      <h1>Sign in</h1>
      <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
      <label>Password<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
      {error && <p className="error">{error}</p>}
      <button type="submit">Sign in</button>
    </form>
  )
}
