import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Verify from './Verify.jsx'
import { verifyAttestation } from '../api.js'
import verifyValid from '../../../fixtures/verify_valid.json'
import verifyNotFound from '../../../fixtures/verify_not_found.json'
import verifyRevoked from '../../../fixtures/verify_revoked.json'
import checks from '../../../fixtures/checks.json'

vi.mock('../api.js', async (importOriginal) => ({
  ...(await importOriginal()),
  verifyAttestation: vi.fn(),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/v/att_Qm3vX9kT2pA']}>
      <Routes>
        <Route path="/v/:id" element={<Verify />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('Verify readability', () => {
  beforeEach(() => {
    verifyAttestation.mockReset()
  })

  it('renders the supplied income period as a readable date range', async () => {
    verifyAttestation.mockResolvedValue(verifyValid)
    renderPage()

    expect(await screen.findByText('1 Apr – 30 Sep 2026')).toBeInTheDocument()
    expect(screen.queryByText('2026-04-01 to 2026-09-30')).not.toBeInTheDocument()
  })

  it('shows each source on separate readable lines with mapped evidence', async () => {
    verifyAttestation.mockResolvedValue(verifyValid)
    const { container } = renderPage()

    await screen.findByText('Valid')
    const sources = container.querySelectorAll('.verify-source')
    expect(sources).toHaveLength(3)
    expect(sources[0].querySelector('.verify-source__label')).toHaveTextContent('Hospitality (casual)')
    expect(sources[0].querySelector('.verify-source__type')).toHaveTextContent('Employment')
    expect(sources[0].querySelector('.verify-source__tier')).toHaveTextContent('Tier A: Third party reported to government')
    expect(sources[0].querySelector('.verify-source__evidence')).toHaveTextContent(
      'Evidence: Government income statement (STP), Bank deposit',
    )
    expect(sources[1].querySelector('.verify-source__evidence')).toHaveTextContent(
      'Evidence: Platform earnings statement, Bank deposit',
    )
    expect(sources[2].querySelector('.verify-source__evidence')).toHaveTextContent(
      'Evidence: Invoice, Bank deposit',
    )
    expect(document.body).not.toHaveTextContent(/stp_income_statement|Stp income statement/)
  })

  it('uses the readable fallback for unknown evidence and readable issue dates', async () => {
    const source = {
      ...verifyValid.attestation.sources[0],
      evidence: ['unfamiliar_evidence'],
    }
    verifyAttestation.mockResolvedValue({
      ...verifyValid,
      attestation: { ...verifyValid.attestation, sources: [source] },
    })
    renderPage()

    expect(await screen.findByText('Evidence: unfamiliar evidence')).toBeInTheDocument()
    expect(screen.getByText('Issued 29 Sep 2026, expires 29 Oct 2026')).toBeInTheDocument()
  })

  it('keeps the verification route free of check content and actions', async () => {
    verifyAttestation.mockResolvedValue(verifyValid)
    renderPage()

    await screen.findByText('Valid')
    expect(screen.queryByRole('button', { name: /explain/i })).not.toBeInTheDocument()
    for (const { title } of checks.checks) {
      expect(document.body).not.toHaveTextContent(title)
    }
  })

  it.each([
    ['revoked', verifyRevoked],
    ['not found', verifyNotFound],
  ])('does not render income details for %s results', async (_status, response) => {
    verifyAttestation.mockResolvedValue(response)
    const { container } = renderPage()

    await screen.findByRole('status')
    expect(container.querySelector('.verify-summary')).toBeNull()
    expect(container.querySelector('.verify-sources')).toBeNull()
  })

  it('shows the range bar for valid results but no monthly chart or checks', async () => {
    verifyAttestation.mockResolvedValue(verifyValid)
    const { container } = renderPage()

    expect(await screen.findByText('Low $2,300')).toBeInTheDocument()
    expect(screen.getByText('High $3,100')).toBeInTheDocument()
    expect(screen.getByText('Median $2,700')).toBeInTheDocument()
    expect(container.querySelector('.monthly-chart')).toBeNull()
    for (const { title } of checks.checks) {
      expect(document.body).not.toHaveTextContent(title)
    }
  })

  it('shows no range bar for revoked results', async () => {
    verifyAttestation.mockResolvedValue(verifyRevoked)
    const { container } = renderPage()
    await screen.findByText('Revoked')
    expect(container.querySelector('.range-bar')).toBeNull()
  })
})
