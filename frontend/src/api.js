// api.js (owner: web-verify), BUILD_GUIDE §9.1. Pages and components call only
// these functions. VITE_USE_FIXTURES (default 'true') returns the committed
// fixtures/*.json unchanged (one exception: createAttestation rewrites verify_url
// onto window.location.origin so a phone on the LAN can open it); otherwise requests go to VITE_API_BASE.
// Env is read at call time so tests can stub it.
const fixtureLoaders = import.meta.glob('../../fixtures/*.json', { import: 'default' })

const fixturesMode = () => (import.meta.env.VITE_USE_FIXTURES ?? 'true') === 'true'
const apiBase = () => import.meta.env.VITE_API_BASE ?? 'http://localhost:8000'

export const keysUrl = () => `${apiBase()}/.well-known/baeslip-keys.json`
export const KEYS_URL = keysUrl()

const fixture = (name) => {
  const load = fixtureLoaders[`../../fixtures/${name}.json`]
  if (!load) return Promise.reject(new Error(`missing fixture ${name}`))
  return load()
}

// Fixture verify_url is hard-coded to localhost; keep its path, use the page's origin.
function withCurrentOrigin(att) {
  if (typeof window === 'undefined') return att
  const url = new URL(att.verify_url)
  return { ...att, verify_url: new URL(url.pathname, window.location.origin).href }
}

const enc = encodeURIComponent

async function request(path, { method = 'GET', body, allow404 = false } = {}) {
  const init = { method }
  if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(body)
  }
  const res = await fetch(apiBase() + path, init)
  if (!res.ok && !(allow404 && res.status === 404)) {
    throw new Error(`${res.status} ${path}`)
  }
  return res.json()
}

// Revoked ids in this browser (fixture mode only). localStorage may throw.
const REVOKED_KEY = 'baeslip.revokedIds'
// localStorage is the source of truth; memoryRevoked only holds ids it refused to store.
const memoryRevoked = new Set()

function readRevoked() {
  const ids = new Set(memoryRevoked)
  try {
    const arr = JSON.parse(localStorage.getItem(REVOKED_KEY) ?? '[]')
    if (Array.isArray(arr)) arr.forEach((id) => ids.add(id))
  } catch {
    // storage unavailable: in-memory ids only
  }
  return ids
}

function markRevoked(id) {
  const ids = readRevoked().add(id)
  try {
    localStorage.setItem(REVOKED_KEY, JSON.stringify([...ids]))
  } catch {
    memoryRevoked.add(id)
  }
}

// GET /workers/{id}/timeline → fixtures/timeline.json
export const getTimeline = (workerId = 'mei') =>
  fixturesMode() ? fixture('timeline') : request(`/workers/${enc(workerId)}/timeline`)

// GET /workers/{id}/checks → fixtures/checks.json
export const getChecks = (workerId = 'mei') =>
  fixturesMode() ? fixture('checks') : request(`/workers/${enc(workerId)}/checks`)

// POST /checks/{check_id}/explain { language } → fixtures/explain.json
export const explainCheck = (checkId, language = 'en') =>
  fixturesMode()
    ? fixture('explain')
    : request(`/checks/${enc(checkId)}/explain`, { method: 'POST', body: { language } })

// POST /attestations/preview { worker_id, scope } → fixtures/preview.json
export const previewAttestation = (workerId = 'mei', scope = 'rental') =>
  fixturesMode()
    ? fixture('preview')
    : request('/attestations/preview', {
        method: 'POST',
        body: { worker_id: workerId, scope },
      })

// POST /attestations { worker_id, scope } → fixtures/attestation.json
export const createAttestation = (workerId = 'mei', scope = 'rental') =>
  fixturesMode()
    ? fixture('attestation').then(withCurrentOrigin)
    : request('/attestations', { method: 'POST', body: { worker_id: workerId, scope } })

// GET /attestations/{id}/verify → fixtures/verify_*.json; 404 resolves to {status:"not_found"}
export async function verifyAttestation(attId) {
  if (!fixturesMode()) {
    return request(`/attestations/${enc(attId)}/verify`, { allow404: true })
  }
  if (readRevoked().has(attId) || attId === 'att_revoked') return fixture('verify_revoked')
  const [valid, expired] = await Promise.all([fixture('verify_valid'), fixture('verify_expired')])
  if (attId === valid.attestation?.attestation_id) return valid
  if (attId === expired.attestation?.attestation_id) return expired
  return fixture('verify_not_found')
}

// POST /attestations/{id}/revoke → fixtures/revoke.json (fixture mode also remembers the id)
export async function revokeAttestation(attId) {
  if (!fixturesMode()) {
    return request(`/attestations/${enc(attId)}/revoke`, { method: 'POST' })
  }
  markRevoked(attId)
  return fixture('revoke')
}

// GET /.well-known/baeslip-keys.json → fixtures/keys.json
export const getKeys = () => (fixturesMode() ? fixture('keys') : request('/.well-known/baeslip-keys.json'))
