import { useCallback, useEffect, useState } from 'react'
import { api, download, type Summary } from '../api'
import { useAuth } from '../auth'
import { useModuleTracking } from '../tracking'

const KV = ({ data }: { data: Record<string, number> }) => (
  <table><tbody>{Object.entries(data).map(([k, v]) => <tr key={k}><td>{k}</td><td>{v}</td></tr>)}</tbody></table>
)

export default function Dashboard() {
  useModuleTracking('dashboard')
  const { user, setDemo } = useAuth()
  const [f, setF] = useState({ date_from: '', date_to: '', status: '', model_version: '' })
  const [s, setS] = useState<Summary | null>(null)
  const [error, setError] = useState('')
  const canExport = user?.role !== 'operator'

  const qs = useCallback(() => {
    const p = new URLSearchParams()
    if (f.date_from) p.set('date_from', `${f.date_from}T00:00:00`)
    if (f.date_to) p.set('date_to', `${f.date_to}T23:59:59`)
    if (f.status) p.set('status', f.status)
    if (f.model_version) p.set('model_version', f.model_version)
    const q = p.toString()
    return q ? `?${q}` : ''
  }, [f])

  useEffect(() => {
    api<Summary>(`/dashboard/summary${qs()}`).then((x) => { setS(x); setDemo(x.is_demo) }).catch((e) => setError(e.message))
  }, [qs, setDemo])

  const exp = (kind: string, fmt: string) => download(`/reports/${kind}.${fmt}${qs()}`).catch((e) => setError(e.message))
  const o = s?.operational

  return (
    <>
      <h1>Dashboard</h1>
      <div className="card row">
        <label>From<input type="date" value={f.date_from} onChange={(e) => setF({ ...f, date_from: e.target.value })} /></label>
        <label>To<input type="date" value={f.date_to} onChange={(e) => setF({ ...f, date_to: e.target.value })} /></label>
        <label>Status
          <select value={f.status} onChange={(e) => setF({ ...f, status: e.target.value })}>
            <option value="">all</option>
            {['created', 'image_uploaded', 'processing', 'completed', 'not_evaluable', 'technical_failure'].map((x) => <option key={x}>{x}</option>)}
          </select>
        </label>
        <label>Model version<input value={f.model_version} onChange={(e) => setF({ ...f, model_version: e.target.value })} placeholder="e.g. demo-0" /></label>
      </div>
      {error && <p className="error">{error}</p>}
      {s && o && (
        <>
          <section className="card">
            <h2>Operational indicators</h2>
            <p>Total cases: <strong>{o.total_cases}</strong> | Technical failures: {o.technical_failures} | Not evaluable: {o.not_evaluable}</p>
            <div className="cols">
              <div><h3>Cases by status</h3><KV data={o.cases_by_status} /></div>
              <div><h3>Results</h3><KV data={o.results_by_outcome} /></div>
              <div><h3>Model versions</h3><KV data={o.inferences_by_model_version} /></div>
            </div>
            <p>Processing time (s): n={o.processing_seconds.n}, mean={o.processing_seconds.mean ?? '-'}, median={o.processing_seconds.median ?? '-'}, max={o.processing_seconds.max ?? '-'}</p>
            <p>Reviews: {o.reviews.total} (agreed {o.reviews.agreed}, disagreed {o.reviews.disagreed})</p>
          </section>
          <section className="card">
            <h2>Scientific metrics {s.scientific.is_demo && <span className="badge demo">DEMO</span>}</h2>
            {s.scientific.available ? <p>Available.</p> : <p className="warn">Not available: {s.scientific.reason}</p>}
          </section>
        </>
      )}
      {canExport ? (
        <section className="card">
          <h2>Export (applies the filters above)</h2>
          {['operational', 'management'].map((k) => (
            <div key={k} className="row">
              <span>{k}</span>
              {['pdf', 'docx', 'xlsx'].map((fmt) => <button key={fmt} onClick={() => exp(k, fmt)}>{fmt.toUpperCase()}</button>)}
            </div>
          ))}
        </section>
      ) : <p><small>Exports are not available for your role.</small></p>}
    </>
  )
}
