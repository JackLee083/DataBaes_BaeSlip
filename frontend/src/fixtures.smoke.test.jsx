// Fixture smoke test (wv-8): real routes through the real api.js in fixture mode.
// Nothing is mocked except global fetch, which must never be called.
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import AppRoutes from './router.jsx'
import verifyValid from '../../fixtures/verify_valid.json'
import verifyExpired from '../../fixtures/verify_expired.json'
import attestation from '../../fixtures/attestation.json'
import checks from '../../fixtures/checks.json'
import schema from '../../schema/attestation.schema.json'

const VALID_ID = verifyValid.attestation.attestation_id
const EXPIRED_ID = verifyExpired.attestation.attestation_id

function escapedSubstringRegExp(value) {
  return new RegExp(value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
}

let fetchMock

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

beforeEach(() => {
  vi.stubEnv('VITE_USE_FIXTURES', 'true')
  fetchMock = vi.fn(() => {
    throw new Error('network used')
  })
  vi.stubGlobal('fetch', fetchMock)
  localStorage.clear()
})

afterEach(() => {
  expect(fetchMock).not.toHaveBeenCalled()
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  localStorage.clear()
})

describe('fixture-mode smoke', () => {
  it(`/v/${VALID_ID} renders valid`, async () => {
    renderAt(`/v/${VALID_ID}`)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Valid'))
    expect(screen.getByText('$2,300–$3,100')).toBeInTheDocument()
    expect(screen.getByText('$2,700')).toBeInTheDocument()
    expect(screen.getByText('6 of 6 months with data')).toBeInTheDocument()
    expect(screen.getByText(
      escapedSubstringRegExp(verifyValid.attestation.issuer.name),
    )).toBeInTheDocument()
  })

  it(`/v/${EXPIRED_ID} renders expired`, async () => {
    renderAt(`/v/${EXPIRED_ID}`)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Expired'))
    expect(screen.getByText(/has expired/)).toBeInTheDocument()
  })

  it('/v/att_revoked renders revoked', async () => {
    renderAt('/v/att_revoked')
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Revoked'))
    expect(screen.getByText('Revoked at 2026-09-29 10:05')).toBeInTheDocument()
    expect(screen.queryByText('$2,700')).not.toBeInTheDocument()
  })

  it('/v/att_nope renders not found', async () => {
    renderAt('/v/att_nope')
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Not found'))
    expect(screen.queryByText('$2,700')).not.toBeInTheDocument()
  })

  it('/spec renders the schema', () => {
    const { container } = renderAt('/spec')
    const pre = container.querySelector('.spec-schema pre')
    expect(pre).not.toBeNull()
    expect(pre.textContent).toBe(JSON.stringify(schema, null, 2))
  })

  it('share flow in fixture mode: preview → create → revoke, then the verify page shows revoked', async () => {
    renderAt('/app')
    fireEvent.click(screen.getByRole('button', { name: 'Preview what will be shared' }))
    fireEvent.click(await screen.findByRole('button', { name: 'Create rental attestation' }))
    const verifyUrl = window.location.origin + new URL(attestation.verify_url).pathname
    const link = await screen.findByRole('link', { name: verifyUrl })
    expect(link).toHaveAttribute('href', verifyUrl)

    fireEvent.click(screen.getByRole('button', { name: 'Revoke' }))
    expect(await screen.findByText(/Revoked at/)).toBeInTheDocument()

    cleanup()
    renderAt(`/v/${attestation.attestation.attestation_id}`)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Revoked'))
  })

  it('/v/:id never shows integrity checks', async () => {
    renderAt(`/v/${VALID_ID}`)
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Valid'))
    const text = document.body.textContent
    expect(checks.checks.length).toBeGreaterThan(0)
    for (const { title } of checks.checks) {
      expect(text).not.toContain(title)
    }
    expect(text).not.toMatch(/hours|visa/i)
  })
})
