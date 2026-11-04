import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, type Case } from '../api'
import { useAuth } from '../auth'
import { useModuleTracking } from '../tracking'

export default function Cases() {
  useModuleTracking('cases')
  const { user, setDemo } = useAuth()
  const nav = useNavigate()
  const [cases, setCases] = useState<Case[]>([])
  const [status, setStatus] = useState('')
  const [institution, setInstitution] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')
  const canCreate = user?.role === 'operator' || user?.role === 'admin'

  useEffect(() => {
    api<Case[]>(`/cases${status ? `?status=${status}` : ''}`)
      .then((c) => { setCases(c); if (c.some((x) => x.latest_inference?.is_demo)) setDemo(true) })
      .catch((e) => setError(e.message))
  }, [status, setDemo])

  const create = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const c = await api<Case>('/cases', { json: { institution: institution || null, notes: notes || null } })
      nav(`/cases/${c.id}`)
    } catch (err) { setError((err as Error).message) }
  }

  return (
    <>
      <h1>Cases</h1>
      {canCreate && (
        <form className="card row" onSubmit={create}>
          <input placeholder="Institution (optional)" value={institution} onChange={(e) => setInstitution(e.target.value)} />
          <input placeholder="Notes (no personal data)" value={notes} onChange={(e) => setNotes(e.target.value)} />
          <button type="submit">New case</button>
          <small>A pseudonymous ID is generated automatically. Do not enter names or document numbers.</small>
        </form>
      )}
      {error && <p className="error">{error}</p>}
      <label>Status{' '}
        <select value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">all</option>
          {['created', 'image_uploaded', 'processing', 'completed', 'not_evaluable', 'technical_failure'].map((s) => <option key={s}>{s}</option>)}
        </select>
      </label>
      <table>
        <thead><tr><th>ID</th><th>Status</th><th>Result</th><th>Created</th></tr></thead>
        <tbody>
          {cases.map((c) => (
            <tr key={c.id}>
              <td><Link to={`/cases/${c.id}`}>{c.pseudonym_id}</Link></td>
              <td>{c.status}</td>
              <td>{c.latest_inference?.label ?? c.latest_inference?.status ?? '-'}</td>
              <td>{new Date(c.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
