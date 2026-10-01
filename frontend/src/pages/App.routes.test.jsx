import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import attestation from '../../../fixtures/attestation.json'
import checksFixture from '../../../fixtures/checks.json'
import explain from '../../../fixtures/explain.json'
import keys from '../../../fixtures/keys.json'
import preview from '../../../fixtures/preview.json'
import timelineFixture from '../../../fixtures/timeline.json'
import verifyExpired from '../../../fixtures/verify_expired.json'
import verifyNotFound from '../../../fixtures/verify_not_found.json'
import verifyRevoked from '../../../fixtures/verify_revoked.json'
import verifyValid from '../../../fixtures/verify_valid.json'
import { verifyAttestation } from '../api.js'
import AppRoutes from '../router.jsx'

vi.mock('../api.js', () => ({
  getTimeline: vi.fn(async () => timelineFixture),
  getChecks: vi.fn(async () => checksFixture),
  explainCheck: vi.fn(async () => explain),
  previewAttestation: vi.fn(async () => preview),
  createAttestation: vi.fn(async () => attestation),
  revokeAttestation: vi.fn(async () => ({ status: 'revoked' })),
  getKeys: vi.fn(async () => keys),
  // The real Verify page links to the issuer keys with keysUrl(); mock the whole api.js surface.
  keysUrl: () => 'http://localhost:8000/.well-known/baeslip-keys.json',
  KEYS_URL: 'http://localhost:8000/.well-known/baeslip-keys.json',
  verifyAttestation: vi.fn(async (id) => {
    if (id === 'att_revoked') return verifyRevoked
    if (id === 'att_expired') return verifyExpired
    if (id === 'att_missing') return verifyNotFound
    return verifyValid
  }),
}))

const expectedBadge = { att_valid: 'Valid', att_revoked: 'Revoked', att_expired: 'Expired', att_missing: 'Not found' }
const checks = checksFixture.checks
const r1 = checks.find((check) => check.rule === 'R1')

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

describe('route isolation', () => {
  beforeEach(() => {
    document.body.innerHTML = ''
  })

  it('/app labels checks as private and not shared, while /v/:id never renders a CheckCard, explanation control, R1 difference or R4 hours', async () => {
    const app = renderAt('/app')
    expect(await screen.findByText(/private/i, { selector: '.private-checks-notice' })).toBeInTheDocument()
    for (const check of checks) {
      expect(await screen.findByRole('heading', { name: check.title })).toBeInTheDocument()
    }
    expect(app.container.querySelectorAll('.check-card')).toHaveLength(checks.length)
    app.unmount()

    const forbidden = [
      'explain in my language',
      'checks for you only',
      r1.title,
      '$221',
      ...checks.map((check) => check.title),
      'hours',
      'visa',
      'shortfall',
      'may be below',
    ].map((text) => text.toLowerCase())

    for (const id of ['att_valid', 'att_revoked', 'att_expired', 'att_missing']) {
      verifyAttestation.mockClear()
      const view = renderAt(`/v/${id}`)
      // The real Verify page calls the API on mount. A placeholder page does not, and
      // then there is nothing to wait for. When it does, wait for its FINAL state before asserting,
      // so the checks below run against the loaded page and not against "Checking".
      if (verifyAttestation.mock.calls.length > 0) {
        await waitFor(() => {
          const badge = view.container.querySelector('.status-badge')
          expect(badge).not.toBeNull()
          expect(badge.dataset.status).not.toBe('loading')
        })
        expect(view.container.querySelector('.status-badge')).toHaveTextContent(expectedBadge[id])
      }
      if (id === 'att_valid') {
        expect(screen.getByRole('link', { name: /issuer public keys/ })).toHaveAttribute(
          'href',
          'http://localhost:8000/.well-known/baeslip-keys.json',
        )
      }
      await new Promise((resolve) => setTimeout(resolve, 20))
      const text = view.container.textContent.toLowerCase()
      for (const word of forbidden) {
        expect(text, `/v/${id} must not contain "${word}"`).not.toContain(word)
      }
      expect(view.container.querySelector('.check-card, .private-checks-notice')).toBeNull()
      expect(screen.queryByRole('button', { name: /explain/i })).toBeNull()
      view.unmount()
    }
  })
})
