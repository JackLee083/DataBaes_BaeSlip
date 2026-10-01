import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import * as api from './api'
import timeline from '../../fixtures/timeline.json'
import checks from '../../fixtures/checks.json'
import explain from '../../fixtures/explain.json'
import preview from '../../fixtures/preview.json'
import attestation from '../../fixtures/attestation.json'
import keys from '../../fixtures/keys.json'
import revoke from '../../fixtures/revoke.json'
import verifyValid from '../../fixtures/verify_valid.json'
import verifyExpired from '../../fixtures/verify_expired.json'
import verifyRevoked from '../../fixtures/verify_revoked.json'
import verifyNotFound from '../../fixtures/verify_not_found.json'

const VALID_ID = 'att_Qm3vX9kT2pA'
const EXPIRED_ID = 'att_Hs8dW1nY4cR'

const jsonResponse = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
})

beforeEach(() => {
  try {
    localStorage.clear()
  } catch {
    // ignore
  }
})

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
})

describe('fixture mode', () => {
  beforeEach(() => {
    vi.stubEnv('VITE_USE_FIXTURES', 'true')
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new Error('network used'))))
  })

  it('each verify state returns its committed fixture', async () => {
    expect(await api.verifyAttestation(VALID_ID)).toEqual(verifyValid)
    expect(await api.verifyAttestation(EXPIRED_ID)).toEqual(verifyExpired)
    expect(await api.verifyAttestation('att_revoked')).toEqual(verifyRevoked)
    expect(await api.verifyAttestation('att_nope')).toEqual(verifyNotFound)
    expect(fetch).not.toHaveBeenCalled()
  })

  it('revoke returns revoke.json and the id then verifies as revoked', async () => {
    const res = await api.revokeAttestation(VALID_ID)
    expect(res.status).toBe(revoke.status)
    expect(res.attestation_id).toBe(revoke.attestation_id)
    expect(res.revoked_at).toBe(revoke.revoked_at)
    expect(res).toEqual(revoke)
    expect(await api.verifyAttestation(VALID_ID)).toEqual(verifyRevoked)
  })

  it('revoked ids live in localStorage, so clearing it restores valid', async () => {
    await api.revokeAttestation(VALID_ID)
    expect(JSON.parse(localStorage.getItem('baeslip.revokedIds'))).toEqual([VALID_ID])
    localStorage.clear()
    expect(await api.verifyAttestation(VALID_ID)).toEqual(verifyValid)
  })

  it('revoke still works when localStorage throws', async () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('quota')
    })
    await api.revokeAttestation(EXPIRED_ID)
    expect(await api.verifyAttestation(EXPIRED_ID)).toEqual(verifyRevoked)
    setItem.mockRestore()
  })

  it('other functions return their fixtures', async () => {
    expect(await api.getTimeline()).toEqual(timeline)
    expect(await api.getChecks()).toEqual(checks)
    expect(await api.explainCheck('r1')).toEqual(explain)
    expect(await api.previewAttestation()).toEqual(preview)
    expect(await api.getKeys()).toEqual(keys)
  })

  it('createAttestation returns the fixture with verify_url on the current origin', async () => {
    const res = await api.createAttestation()
    const path = new URL(attestation.verify_url).pathname
    expect(res.verify_url.startsWith(window.location.origin)).toBe(true)
    expect(res.verify_url.endsWith(path)).toBe(true)
    expect(res).toEqual({ ...attestation, verify_url: window.location.origin + path })
  })

  it('createAttestation does not mutate the imported fixture', async () => {
    const before = structuredClone(attestation)
    const res = await api.createAttestation()
    expect(res).not.toBe(attestation)
    expect(attestation).toEqual(before)
  })
})

describe('live mode', () => {
  let fetchMock
  beforeEach(() => {
    vi.stubEnv('VITE_USE_FIXTURES', 'false')
    vi.stubEnv('VITE_API_BASE', 'http://api.test')
    fetchMock = vi.fn(async () => jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)
  })

  it('POSTs {worker_id, scope} to /attestations', async () => {
    await api.createAttestation('mei', 'rental')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://api.test/attestations')
    expect(init.method).toBe('POST')
    expect(init.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(init.body)).toEqual({ worker_id: 'mei', scope: 'rental' })
  })

  it('verify 404 resolves to {status:"not_found"}', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ status: 'not_found' }, 404))
    await expect(api.verifyAttestation('att_x')).resolves.toEqual({ status: 'not_found' })
    expect(fetchMock.mock.calls[0][0]).toBe('http://api.test/attestations/att_x/verify')
  })

  it('non-404 error rejects with status and path', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, 500))
    await expect(api.getChecks('mei')).rejects.toThrow('500 /workers/mei/checks')
  })

  it('explain posts {language}', async () => {
    await api.explainCheck('chk 1', 'en')
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('http://api.test/checks/chk%201/explain')
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({ language: 'en' })
  })

  it('keysUrl uses VITE_API_BASE', () => {
    expect(api.keysUrl()).toBe('http://api.test/.well-known/baeslip-keys.json')
  })

  it('getKeys requests the BaeSlip public-keys endpoint', async () => {
    const result = await api.getKeys()
    expect(result).toEqual({ ok: true })
    expect(fetchMock).toHaveBeenCalledWith(
      'http://api.test/.well-known/baeslip-keys.json',
      { method: 'GET' },
    )
  })
})

it('HTML document title is BaeSlip', () => {
  const html = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8')
  expect(html).toContain('<title>BaeSlip</title>')
})
