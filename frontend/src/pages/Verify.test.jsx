// Tests for the landlord verify page.
import { render, screen, fireEvent, cleanup } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import Verify from './Verify.jsx'
import { verifyAttestation } from '../api.js'
import verifyValid from '../../../fixtures/verify_valid.json'
import verifyExpired from '../../../fixtures/verify_expired.json'
import verifyRevoked from '../../../fixtures/verify_revoked.json'
import verifyNotFound from '../../../fixtures/verify_not_found.json'
import checks from '../../../fixtures/checks.json'

vi.mock('../api.js', () => ({
  verifyAttestation: vi.fn(),
  keysUrl: () => 'http://api.test/.well-known/baeslip-keys.json',
}))

const ID = 'att_Qm3vX9kT2pA'

function escapedSubstringRegExp(value) {
  return new RegExp(value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/v/${ID}`]}>
      <Routes>
        <Route path="/v/:id" element={<Verify />} />
      </Routes>
    </MemoryRouter>,
  )
}

beforeEach(() => {
  verifyAttestation.mockReset()
})

describe('Verify page', () => {
  it('verify_valid.json shows range, median and coverage', async () => {
    verifyAttestation.mockResolvedValue(verifyValid)
    renderPage()
    expect(await screen.findByText(
      escapedSubstringRegExp(verifyValid.attestation.issuer.name),
    )).toBeInTheDocument()
    cleanup()

    const responseWithDistinctIssuer = {
      ...verifyValid,
      attestation: {
        ...verifyValid.attestation,
        issuer: {
          ...verifyValid.attestation.issuer,
          name: 'A different issuer (test copy) [v2]?',
        },
      },
    }
    verifyAttestation.mockResolvedValue(responseWithDistinctIssuer)
    renderPage()
    expect(screen.getByText(new RegExp(ID))).toBeInTheDocument()
    expect(await screen.findByText('Valid')).toBeInTheDocument()
    expect(screen.getByText('$2,300–$3,100')).toBeInTheDocument()
    expect(screen.getByText('$2,700')).toBeInTheDocument()
    expect(screen.getByText(/6 of 6 months with data/)).toBeInTheDocument()
    expect(screen.getByText(/Mei L\./)).toBeInTheDocument()
    expect(screen.getByText('Hospitality (casual)')).toBeInTheDocument()
    expect(screen.getByText('Food delivery platform')).toBeInTheDocument()
    expect(screen.getByText('Overseas design contracts')).toBeInTheDocument()
    expect(screen.getByText(
      escapedSubstringRegExp(responseWithDistinctIssuer.attestation.issuer.name),
    )).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /issuer public keys/ }),
    ).toHaveAttribute('href', 'http://api.test/.well-known/baeslip-keys.json')
    expect(verifyAttestation).toHaveBeenCalledWith(ID)
  })

  it('verify_expired.json shows expired', async () => {
    verifyAttestation.mockResolvedValue(verifyExpired)
    renderPage()
    expect(await screen.findByText('Expired')).toBeInTheDocument()
    expect(screen.getByText(/This attestation has expired/)).toBeInTheDocument()
  })

  it('verify_revoked.json shows revoked and revoked_at', async () => {
    verifyAttestation.mockResolvedValue(verifyRevoked)
    renderPage()
    expect(await screen.findByText('Revoked')).toBeInTheDocument()
    expect(screen.getByText(/Revoked at 2026-09-29 10:05/)).toBeInTheDocument()
    expect(screen.queryByText('$2,700')).toBeNull()
    expect(screen.queryByText('Hospitality (casual)')).toBeNull()
  })

  it('verify_not_found.json shows not found and no summary', async () => {
    verifyAttestation.mockResolvedValue(verifyNotFound)
    const { container } = renderPage()
    expect(await screen.findByText('Not found')).toBeInTheDocument()
    expect(screen.getByText(/No attestation with this ID exists/)).toBeInTheDocument()
    expect(container.querySelector('.verify-summary')).toBeNull()
  })

  it('signature_valid false shows the warning', async () => {
    verifyAttestation.mockResolvedValue({ ...verifyValid, signature_valid: false })
    const { container } = renderPage()
    expect(await screen.findByText('Signature invalid')).toBeInTheDocument()
    expect(container.querySelector('.signature-warning')).toBeInTheDocument()
  })

  it('page text contains no hours, visa or check titles', async () => {
    verifyAttestation.mockResolvedValue(verifyValid)
    renderPage()
    await screen.findByText('Valid')
    const text = document.body.textContent
    expect(text).not.toMatch(/hours|visa|transaction/i)
    for (const check of checks.checks) {
      expect(text).not.toContain(check.title)
    }
  })

  it('a network error shows an alert and retry re-calls verify', async () => {
    verifyAttestation.mockRejectedValueOnce(new Error('network'))
    verifyAttestation.mockResolvedValueOnce(verifyValid)
    renderPage()
    expect(await screen.findByRole('alert')).toHaveTextContent(/Could not reach the issuer/)
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByText('Valid')).toBeInTheDocument()
    expect(verifyAttestation).toHaveBeenCalledTimes(2)
  })
})
