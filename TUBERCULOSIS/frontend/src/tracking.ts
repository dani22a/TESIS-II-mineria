import { useEffect } from 'react'
import { API, getToken } from './api'

// One module is "active" at a time. Events carry a client_event_id so retries are idempotent server-side.
let active: { module: string; exitId: string } | null = null

const uuid = () => crypto.randomUUID()

function send(event: 'module_enter' | 'module_exit', module: string, id: string) {
  const t = getToken()
  if (!t) return
  // keepalive lets the request outlive page unload (sendBeacon cannot set the Authorization header)
  fetch(`${API}/audit/module-events`, {
    method: 'POST',
    keepalive: true,
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${t}` },
    body: JSON.stringify({ event, module, client_event_id: id }),
  }).catch(() => {})
}

export function enterModule(module: string) {
  active = { module, exitId: uuid() }
  send('module_enter', module, uuid())
  return active
}

export function exitModule(entry: { module: string; exitId: string }) {
  if (active !== entry) return // already exited (e.g. by logout)
  active = null
  send('module_exit', entry.module, entry.exitId)
}

/** For logout: returns the body fields so the server records the exit in the same request. */
export function takeActiveForLogout(): { active_module?: string; client_event_id?: string } {
  const a = active
  active = null
  return a ? { active_module: a.module, client_event_id: a.exitId } : {}
}

export function useModuleTracking(module: string) {
  useEffect(() => {
    const entry = enterModule(module)
    const onHide = () => exitModule(entry)
    window.addEventListener('pagehide', onHide)
    return () => {
      window.removeEventListener('pagehide', onHide)
      exitModule(entry)
    }
  }, [module])
}
