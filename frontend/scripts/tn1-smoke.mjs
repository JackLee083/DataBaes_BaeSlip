// TN1 live smoke (owner: web-verify). Exercises issue -> verify -> SPA page -> revoke -> verify
// against a running backend and Vite dev server. Not part of `npm test`; needs Node >= 22.
// Run: API_BASE=http://localhost:8000 WORKER_ID=mei node frontend/scripts/tn1-smoke.mjs
// Backend needs PUBLIC_WEB_URL=<vite origin>; frontend: VITE_USE_FIXTURES=false npm run dev -- --host
// Exits 1 on the first mismatch, printing one line per step.
import { readFileSync } from 'node:fs'

const API_BASE = (process.env.API_BASE || 'http://localhost:8000').replace(/\/$/, '')
const WORKER_ID = process.env.WORKER_ID || 'mei'

const ok = (n, msg) => console.log(`ok ${n} ${msg}`)
const fail = (n, msg, expected, got) => {
  console.log(`FAIL ${n} ${msg}: expected ${expected}, got ${got}`)
  process.exit(1)
}
const check = (n, msg, expected, got) => {
  if (expected !== got) fail(n, msg, JSON.stringify(expected), JSON.stringify(got))
}
const canon = (v) => {
  if (Array.isArray(v)) return `[${v.map(canon).join(',')}]`
  if (v && typeof v === 'object') {
    return `{${Object.keys(v).sort().map((k) => `${JSON.stringify(k)}:${canon(v[k])}`).join(',')}}`
  }
  return JSON.stringify(v)
}
const call = async (n, msg, url, init) => {
  try {
    return await fetch(url, init)
  } catch (e) {
    return fail(n, msg, 'a response', `network error ${e.cause?.code || e.message}`)
  }
}
const json = async (n, msg, res) => {
  const text = await res.text()
  try {
    return JSON.parse(text)
  } catch {
    return fail(n, msg, 'JSON body', text.slice(0, 120))
  }
}

// 1 issue
let res = await call(1, 'POST /attestations', `${API_BASE}/attestations`, {
  method: 'POST',
  headers: { 'content-type': 'application/json' },
  body: JSON.stringify({ worker_id: WORKER_ID, scope: 'rental' }),
})
check(1, 'POST /attestations status', 200, res.status)
const issued = await json(1, 'POST /attestations', res)
const att = issued.attestation
if (!att || !issued.verify_url) fail(1, 'body has attestation and verify_url', 'both', Object.keys(issued).join(','))
const id = att.attestation_id
check(1, 'attestation_id prefix', true, typeof id === 'string' && id.startsWith('att_'))
check(1, 'signature.alg', 'Ed25519', att.signature?.alg)
check(1, 'verify_url suffix', true, issued.verify_url.endsWith(`/v/${id}`))
ok(1, `issued ${id}`)

// 2 verify + CORS
const origin = new URL(issued.verify_url).origin
res = await call(2, 'GET verify', `${API_BASE}/attestations/${id}/verify`, { headers: { origin } })
check(2, 'verify status', 200, res.status)
let body = await json(2, 'GET verify', res)
check(2, 'status', 'valid', body.status)
check(2, 'signature_valid', true, body.signature_valid)
check(2, 'attestation equals issued', canon(att), canon(body.attestation))
const acao = res.headers.get('access-control-allow-origin')
check(2, `access-control-allow-origin for ${origin}`, true, acao === origin || acao === '*')
ok(2, `verify valid, signature_valid, CORS ${acao}`)

// 3 SPA page
res = await call(3, 'GET verify_url', issued.verify_url)
check(3, 'verify_url status', 200, res.status)
const html = await res.text()
check(3, 'body contains <div id="root">', true, html.includes('<div id="root">'))
ok(3, `SPA served at ${issued.verify_url}`)

// 4 revoke
res = await call(4, 'POST revoke', `${API_BASE}/attestations/${id}/revoke`, { method: 'POST' })
check(4, 'revoke status', 200, res.status)
body = await json(4, 'POST revoke', res)
const want = Object.keys(JSON.parse(readFileSync(new URL('../../fixtures/revoke.json', import.meta.url), 'utf8'))).sort()
check(4, 'revoke keys', want.join(','), Object.keys(body).sort().join(','))
check(4, 'status', 'revoked', body.status)
check(4, 'attestation_id', id, body.attestation_id)
ok(4, 'revoked')

// 5 verify after revoke
res = await call(5, 'GET verify', `${API_BASE}/attestations/${id}/verify`)
check(5, 'verify status', 200, res.status)
body = await json(5, 'GET verify', res)
check(5, 'status', 'revoked', body.status)
check(5, 'revoked_at present', true, Boolean(body.revoked_at))
ok(5, `verify revoked at ${body.revoked_at}`)

// 6 not found
res = await call(6, 'GET verify unknown', `${API_BASE}/attestations/att_does_not_exist/verify`)
check(6, 'not_found status', 404, res.status)
body = await json(6, 'GET verify unknown', res)
check(6, 'body', canon({ status: 'not_found' }), canon(body))
ok(6, 'unknown id is 404 not_found')

// 7 keys
res = await call(7, 'GET keys', `${API_BASE}/.well-known/baeslip-keys.json`)
check(7, 'keys status', 200, res.status)
body = await json(7, 'GET keys', res)
check(7, 'keys[0].alg', 'Ed25519', body.keys?.[0]?.alg)
ok(7, 'keys published')
