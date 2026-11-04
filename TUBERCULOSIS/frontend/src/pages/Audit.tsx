import { useEffect, useState } from 'react'
import { api, type AuditRow } from '../api'
import { useModuleTracking } from '../tracking'

const MODULES = ['auth', 'cases', 'upload', 'results', 'review', 'dashboard', 'audit', 'users', 'reports']

export default function Audit() {
  useModuleTracking('audit')
  const [f, setF] = useState({ module: '', event: '', outcome: '', user_id: '', date_from: '', date_to: '' })
  const [rows, setRows] = useState<AuditRow[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    const p = new URLSearchParams({ limit: '200' })
    Object.entries(f).forEach(([k, v]) => {
      if (!v) return
      p.set(k, k === 'date_from' ? `${v}T00:00:00` : k === 'date_to' ? `${v}T23:59:59` : v)
    })
    api<AuditRow[]>(`/audit?${p}`).then(setRows).catch((e) => setError(e.message))
  }, [f])

  const set = (k: string) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  return (
    <>
      <h1>Audit log</h1>
      <div className="card row">
        <label>Module<select value={f.module} onChange={set('module')}><option value="">all</option>{MODULES.map((m) => <option key={m}>{m}</option>)}</select></label>
        <label>Event<input value={f.event} onChange={set('event')} /></label>
        <label>Outcome<select value={f.outcome} onChange={set('outcome')}><option value="">all</option><option>success</option><option>failure</option><option>denied</option></select></label>
        <label>User ID<input value={f.user_id} onChange={set('user_id')} size={5} /></label>
        <label>From<input type="date" value={f.date_from} onChange={set('date_from')} /></label>
        <label>To<input type="date" value={f.date_to} onChange={set('date_to')} /></label>
      </div>
      {error && <p className="error">{error}</p>}
      <table>
        <thead><tr><th>When</th><th>User</th><th>Module</th><th>Event</th><th>Outcome</th><th>Detail</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{new Date(r.created_at).toLocaleString()}</td><td>{r.user_email ?? '-'}</td>
              <td>{r.module}</td><td>{r.event}</td><td>{r.outcome}</td><td><code>{r.detail ?? ''}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
