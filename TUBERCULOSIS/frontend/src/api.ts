export const API = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

export type Role = 'admin' | 'operator' | 'reviewer' | 'auditor'

let token: string | null = sessionStorage.getItem('tb_token')
export const getToken = () => token
export function setToken(t: string | null) {
  token = t
  if (t) sessionStorage.setItem('tb_token', t)
  else sessionStorage.removeItem('tb_token')
}

let onUnauthorized: () => void = () => {}
export const setUnauthorizedHandler = (fn: () => void) => { onUnauthorized = fn }

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message) }
}

function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
  return token ? { ...extra, Authorization: `Bearer ${token}` } : extra
}

async function failure(r: Response): Promise<ApiError> {
  let msg = r.statusText
  try {
    const j = await r.json()
    msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail ?? j)
  } catch { /* not JSON */ }
  return new ApiError(r.status, msg)
}

export async function api<T>(path: string, init: { method?: string; json?: unknown; form?: FormData } = {}): Promise<T> {
  const headers = authHeaders(init.json !== undefined ? { 'Content-Type': 'application/json' } : {})
  const r = await fetch(API + path, {
    method: init.method ?? (init.json !== undefined || init.form ? 'POST' : 'GET'),
    headers,
    body: init.form ?? (init.json !== undefined ? JSON.stringify(init.json) : undefined),
  })
  if (r.status === 401 && path !== '/auth/login') onUnauthorized()
  if (!r.ok) throw await failure(r)
  return r.status === 204 ? (undefined as T) : r.json()
}

export async function fetchBlob(path: string): Promise<{ blob: Blob; filename: string }> {
  const r = await fetch(API + path, { headers: authHeaders() })
  if (r.status === 401) onUnauthorized()
  if (!r.ok) throw await failure(r)
  const cd = r.headers.get('Content-Disposition') ?? ''
  return { blob: await r.blob(), filename: /filename="?([^";]+)"?/.exec(cd)?.[1] ?? 'download' }
}

export async function download(path: string) {
  const { blob, filename } = await fetchBlob(path)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export interface Inference {
  id: number; case_id: number; status: 'completed' | 'not_evaluable' | 'technical_failure'
  label: string | null; score: number | null; threshold: number; model_version: string
  is_demo: boolean; error_message: string | null; has_heatmap: boolean; created_at: string
}
export interface Case {
  id: number; pseudonym_id: string; institution: string | null; notes: string | null; status: string
  created_at: string; has_image: boolean; qc_passed: boolean | null; qc_reason: string | null
  latest_inference: Inference | null
}
export interface AuditRow {
  id: number; created_at: string; user_id: number | null; user_email: string | null
  session_id: string | null; module: string; event: string; outcome: string; detail: string | null
}
export interface Summary {
  generated_at: string; filters: Record<string, string>; is_demo: boolean; demo_notice: string | null
  operational: {
    total_cases: number; cases_by_status: Record<string, number>
    results_by_outcome: Record<string, number>; inferences_by_model_version: Record<string, number>
    processing_seconds: { n: number; mean: number | null; median: number | null; max: number | null }
    technical_failures: number; not_evaluable: number
    reviews: { total: number; agreed: number; disagreed: number }
  }
  scientific: { available: boolean; is_demo: boolean; reason: string }
}
