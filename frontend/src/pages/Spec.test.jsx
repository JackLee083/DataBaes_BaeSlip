// Tests for the BaeSlip standard spec page (owner: web-verify, ticket F6).
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import schema from '../../../schema/attestation.schema.json'
import Spec from './Spec.jsx'

vi.mock('../api.js', () => ({
  keysUrl: () => 'http://api.test/.well-known/baeslip-keys.json',
}))

function renderSpec() {
  return render(<Spec />)
}

function cellsOfRow(label) {
  const row = screen.getByRole('row', { name: new RegExp(label, 'i') })
  return within(row).getAllByRole('cell')
}

describe('Spec page', () => {
  it('lists tiers A–D and every forbidden field', () => {
    const { container } = renderSpec()
    expect(screen.getByRole('heading', { level: 1, name: /BaeSlip standard/ })).toBeInTheDocument()
    expect(screen.getByText(/BaeSlip is an open standard for income attestations/i)).toBeInTheDocument()
    expect(screen.getByText(/Version 0\.1/)).toBeInTheDocument()

    const tiers = within(container.querySelector('.spec-tiers'))
    for (const letter of ['A', 'B', 'C', 'D']) {
      expect(tiers.getByRole('cell', { name: letter })).toBeInTheDocument()
    }
    expect(tiers.getByText(/reported to (the )?government/i)).toBeInTheDocument()
    expect(tiers.getByRole('cell', { name: /^confirmed by the payer$/i })).toBeInTheDocument()
    expect(tiers.getByText(/matched to a bank deposit/i)).toBeInTheDocument()
    expect(tiers.getByText(/self-reported only/i)).toBeInTheDocument()
    expect(tiers.getByText(/weakest month/i)).toBeInTheDocument()

    const forbidden = within(container.querySelector('.spec-forbidden'))
    expect(forbidden.getByText(/hours worked/i)).toBeInTheDocument()
    expect(forbidden.getByText(/visa status/i)).toBeInTheDocument()
    expect(forbidden.getByText(/individual transactions/i)).toBeInTheDocument()
    expect(forbidden.getByText(/integrity-check results/i)).toBeInTheDocument()
  })

  it('renders the JSON schema from the contract file', () => {
    const { container } = renderSpec()
    const pre = container.querySelector('.spec-schema pre')
    expect(pre.textContent).toBe(JSON.stringify(schema, null, 2))
    expect(pre.textContent).toContain('$defs')
    expect(pre.textContent).toContain('Attestation')
  })

  it('scope table marks forbidden items No for both scopes and monthly series lending-only', () => {
    renderSpec()
    const forbidden = cellsOfRow('forbidden')
    expect(forbidden.slice(-2).map((c) => c.textContent)).toEqual(['No', 'No'])
    const series = cellsOfRow('monthly series')
    expect(series.slice(-2).map((c) => c.textContent)).toEqual(['No', 'Yes'])
    const perSource = cellsOfRow('per-source monthly')
    expect(perSource.slice(-2).map((c) => c.textContent)).toEqual(['No', 'Yes'])
    const range = cellsOfRow('range and median')
    expect(range.slice(-2).map((c) => c.textContent)).toEqual(['Yes', 'Yes'])
  })

  it('links to the issuer public keys', () => {
    renderSpec()
    expect(screen.getByRole('link', { name: /Issuer public keys/i })).toHaveAttribute(
      'href',
      'http://api.test/.well-known/baeslip-keys.json',
    )
  })

  it('explains that status is not signed and expiry is 30 days', () => {
    const { container } = renderSpec()
    const signing = within(container.querySelector('.spec-signing'))
    expect(signing.getByText(/Ed25519/)).toBeInTheDocument()
    expect(signing.getByText(/not signed/i)).toBeInTheDocument()
    expect(signing.getByText(/no re-signing/i)).toBeInTheDocument()
    expect(signing.getByText(/30 days after issue/i)).toBeInTheDocument()
  })
})
