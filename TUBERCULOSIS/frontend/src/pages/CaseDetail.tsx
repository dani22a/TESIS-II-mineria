import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { api, fetchBlob, type Case, type Inference } from '../api'
import { useAuth } from '../auth'
import { useModuleTracking } from '../tracking'

function Blob({ path, alt }: { path: string; alt: string }) {
  const [src, setSrc] = useState('')
  useEffect(() => {
    let url = ''
    fetchBlob(path).then(({ blob }) => { url = URL.createObjectURL(blob); setSrc(url) }).catch(() => {})
    return () => { if (url) URL.revokeObjectURL(url) }
  }, [path])
  return src ? <img src={src} alt={alt} /> : null
}

function ResultCard({ inf }: { inf: Inference }) {
  return (
    <div className="card">
      <h2>Result {inf.is_demo && <span className="badge demo">DEMO</span>}</h2>
      {inf.status === 'completed' && (
        <>
          <p><strong>{inf.label}</strong></p>
          <p>Probability: {inf.score?.toFixed(3)} (threshold {inf.threshold})</p>
        </>
      )}
      {inf.status === 'not_evaluable' && <p className="warn">Not evaluable: {inf.error_message ?? 'image did not pass quality control'}. This is not a negative result.</p>}
      {inf.status === 'technical_failure' && <p className="error">Technical failure: {inf.error_message}. Re-run the analysis.</p>}
      <p><small>Model version: {inf.model_version} - {new Date(inf.created_at).toLocaleString()}</small></p>
    </div>
  )
}

export default function CaseDetail() {
  useModuleTracking('results')
  const id = Number(useParams().id)
  const { user, setDemo } = useAuth()
  const [c, setC] = useState<Case | null>(null)
  const [error, setError] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [agrees, setAgrees] = useState(true)
  const [finalLabel, setFinalLabel] = useState('no_compatible_findings')
  const [comment, setComment] = useState('')
  const [msg, setMsg] = useState('')
  const role = user?.role
  const canOperate = role === 'operator' || role === 'admin'
  const canReview = role === 'reviewer' || role === 'admin'

  const load = useCallback(() => {
    api<Case>(`/cases/${id}`).then((x) => { setC(x); if (x.latest_inference?.is_demo) setDemo(true) }).catch((e) => setError(e.message))
  }, [id, setDemo])
  useEffect(load, [load])

  const run = async (fn: () => Promise<unknown>, ok = '') => {
    setError(''); setMsg('')
    try { await fn(); setMsg(ok); load() } catch (e) { setError((e as Error).message) }
  }

  const upload = (e: FormEvent) => {
    e.preventDefault()
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    run(() => api(`/cases/${id}/image`, { form }), 'Image uploaded.')
  }
  const review = (e: FormEvent) => {
    e.preventDefault()
    run(() => api(`/cases/${id}/reviews`, { json: { agrees, final_label: finalLabel, comment: comment || null } }), 'Evaluation saved.')
  }

  if (!c) return error ? <p className="error">{error}</p> : <p>Loading...</p>
  const inf = c.latest_inference
  return (
    <>
      <h1>Case {c.pseudonym_id} <span className="badge">{c.status}</span></h1>
      {error && <p className="error">{error}</p>}
      {msg && <p className="ok">{msg}</p>}

      {!c.has_image && canOperate && (
        <form className="card" onSubmit={upload}>
          <h2>Upload chest X-ray</h2>
          <input type="file" accept="image/png,image/jpeg,.dcm" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <button type="submit" disabled={!file}>Upload</button>
        </form>
      )}
      {c.has_image && c.qc_passed === false && <p className="warn">Quality control failed: {c.qc_reason}</p>}

      <div className="images">
        {c.has_image && <figure><Blob path={`/cases/${id}/image`} alt="Chest X-ray" /><figcaption>X-ray</figcaption></figure>}
        {inf?.has_heatmap && <figure><Blob path={`/cases/${id}/inferences/${inf.id}/heatmap`} alt="Heatmap overlay" /><figcaption>Heatmap overlay{inf.is_demo ? ' (synthetic, DEMO)' : ''}</figcaption></figure>}
      </div>

      {c.has_image && canOperate && (
        <button onClick={() => run(() => api(`/cases/${id}/inference`, { method: 'POST' }), 'Analysis finished.')}>
          {inf ? 'Re-run analysis' : 'Run analysis'}
        </button>
      )}
      {inf && <ResultCard inf={inf} />}

      {inf && inf.status !== 'technical_failure' && canReview && (
        <form className="card" onSubmit={review}>
          <h2>Reviewer evaluation</h2>
          <label><input type="checkbox" checked={agrees} onChange={(e) => setAgrees(e.target.checked)} /> I agree with the model output</label>
          <label>Final label
            <select value={finalLabel} onChange={(e) => setFinalLabel(e.target.value)}>
              <option value="probable_tuberculosis">probable_tuberculosis</option>
              <option value="no_compatible_findings">no_compatible_findings</option>
              <option value="not_evaluable">not_evaluable</option>
            </select>
          </label>
          <label>Comment<textarea value={comment} onChange={(e) => setComment(e.target.value)} maxLength={2000} /></label>
          <button type="submit">Save evaluation</button>
        </form>
      )}
    </>
  )
}
