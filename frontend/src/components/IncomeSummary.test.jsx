import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import preview from '../../../fixtures/preview.json'
import IncomeSummary from './IncomeSummary.jsx'
import { previewAttestation } from '../api.js'

vi.mock('../api.js', () => ({
  previewAttestation: vi.fn(),
}))

const summary = preview.attestation.summary
const sources = preview.attestation.sources
const money = (n) => '$' + n.toLocaleString('en-US')

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('IncomeSummary', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('shows the preview summary figures exactly as supplied', async () => {
    previewAttestation.mockResolvedValue(preview)

    render(<IncomeSummary onCreateProof={() => {}} />)

    const { low, high } = summary.monthly_income_range
    const { months_with_data, months_in_period } = summary.coverage
    expect(await screen.findByText(`${money(low)}–${money(high)}`)).toBeInTheDocument()
    expect(screen.getByText(money(summary.monthly_median))).toBeInTheDocument()
    expect(screen.getByText(`${months_with_data} of ${months_in_period} months with data`)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Income summary' })).toBeInTheDocument()
    expect(previewAttestation).toHaveBeenCalledWith('mei', 'rental')
  })

  it('displays supplied values without recomputing them', async () => {
    const custom = structuredClone(preview)
    custom.attestation.summary.monthly_income_range = { low: 1111, high: 9999 }
    custom.attestation.summary.monthly_median = 5555
    custom.attestation.summary.coverage = { months_with_data: 4, months_in_period: 6 }
    previewAttestation.mockResolvedValue(custom)

    render(<IncomeSummary onCreateProof={() => {}} />)

    expect(await screen.findByText('$1,111–$9,999')).toBeInTheDocument()
    expect(screen.getByText('$5,555')).toBeInTheDocument()
    expect(screen.getByText('4 of 6 months with data')).toBeInTheDocument()
  })

  it('lists each source label with its tier letter', async () => {
    previewAttestation.mockResolvedValue(preview)

    const { container } = render(<IncomeSummary onCreateProof={() => {}} />)

    await screen.findByText(money(summary.monthly_median))
    for (const source of sources) {
      expect(screen.getByText(source.label)).toBeInTheDocument()
    }
    const badges = [...container.querySelectorAll('[data-tier]')]
    expect(badges.map((b) => b.getAttribute('data-tier'))).toEqual(sources.map((s) => s.tier))
    badges.forEach((badge, i) => expect(badge.textContent).toContain(sources[i].tier))
  })

  it('shows a loading status while the request is pending', () => {
    previewAttestation.mockReturnValue(deferred().promise)

    render(<IncomeSummary onCreateProof={() => {}} />)

    expect(screen.getByRole('status')).toHaveTextContent('Loading income summary...')
  })

  it('a rejection shows an alert and Retry reloads the figures', async () => {
    previewAttestation.mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(preview)

    render(<IncomeSummary onCreateProof={() => {}} />)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Unable to load the income summary.')
    fireEvent.click(within(alert).getByRole('button', { name: 'Retry' }))

    expect(await screen.findByText(money(summary.monthly_median))).toBeInTheDocument()
    expect(previewAttestation).toHaveBeenCalledTimes(2)
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument())
  })

  it('ignores results that resolve after unmount', async () => {
    const d = deferred()
    previewAttestation.mockReturnValue(d.promise)
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { unmount } = render(<IncomeSummary onCreateProof={() => {}} />)
    unmount()
    await act(async () => {
      d.resolve(preview)
      await Promise.resolve()
    })

    expect(errorSpy).not.toHaveBeenCalled()
    errorSpy.mockRestore()
  })

  it('the Create a rental proof button calls onCreateProof and is present while loading', async () => {
    const d = deferred()
    previewAttestation.mockReturnValue(d.promise)
    const onCreateProof = vi.fn()

    render(<IncomeSummary onCreateProof={onCreateProof} />)

    const button = screen.getByRole('button', { name: 'Create a rental proof' })
    expect(button).toHaveClass('primary-action')
    fireEvent.click(button)
    expect(onCreateProof).toHaveBeenCalledTimes(1)

    await act(async () => {
      d.resolve(preview)
    })
    expect(screen.getByRole('button', { name: 'Create a rental proof' })).toBeInTheDocument()
  })

  it('shows the range bar with the supplied low, high and median', async () => {
    previewAttestation.mockResolvedValue(preview)
    render(<IncomeSummary onCreateProof={() => {}} />)
    const { low, high } = summary.monthly_income_range
    expect(await screen.findByText(`Low ${money(low)}`)).toBeInTheDocument()
    expect(screen.getByText(`High ${money(high)}`)).toBeInTheDocument()
    expect(screen.getByRole('img', { name: /Monthly income range/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Create a rental proof' })).toBeInTheDocument()
  })
})
