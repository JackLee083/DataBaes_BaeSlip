import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'
import checksFixture from '../../../fixtures/checks.json'
import CheckVisual from './CheckVisual'

const checkFor = (rule) => checksFixture.checks.find((check) => check.rule === rule)

describe('CheckVisual', () => {
  afterEach(cleanup)

  it('R1 shows expected and paid bars with supplied dollar values', () => {
    render(<CheckVisual check={checkFor('R1')} />)

    const img = screen.getByRole('img')
    expect(img).toHaveAttribute('aria-label', expect.stringContaining('$661.00'))
    expect(img).toHaveAttribute('aria-label', expect.stringContaining('$440.00'))
    expect(screen.getByText('Expected $661.00')).toBeInTheDocument()
    expect(screen.getByText('Paid $440.00')).toBeInTheDocument()
    expect(img).toHaveAttribute('viewBox')
  })

  it('R2 shows expected and paid bars', () => {
    render(<CheckVisual check={checkFor('R2')} />)

    expect(screen.getByText('Expected $281.70')).toBeInTheDocument()
    expect(screen.getByText('Paid $250.00')).toBeInTheDocument()
  })

  it('R3 shows payday, deadline and received dates with received marked late', () => {
    render(<CheckVisual check={checkFor('R3')} />)

    expect(screen.getByText('Payday 16 Sep 2026')).toBeInTheDocument()
    expect(screen.getByText('Deadline 25 Sep 2026')).toBeInTheDocument()
    expect(screen.getByText('Received 28 Sep 2026 (late)')).toBeInTheDocument()
    const label = screen.getByRole('img').getAttribute('aria-label')
    expect(label).toContain('16 Sep 2026')
    expect(label).toContain('25 Sep 2026')
    expect(label).toContain('28 Sep 2026')
  })

  it('R4 shows a gauge with the total, limit and warning marker', () => {
    render(<CheckVisual check={checkFor('R4')} />)

    expect(screen.getByText('50 h')).toBeInTheDocument()
    expect(screen.getByText('48 h limit')).toBeInTheDocument()
    expect(screen.getByText('44 h warn')).toBeInTheDocument()
    expect(screen.getByRole('img')).toHaveAttribute('aria-label', expect.stringContaining('50 of 48 hours'))
  })

  it('renders nothing for an unknown rule or missing fields', () => {
    const { container, rerender } = render(<CheckVisual check={{ rule: 'R9' }} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<CheckVisual check={{ rule: 'R1' }} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<CheckVisual check={{ rule: 'R4', facts: {} }} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<CheckVisual check={{ rule: 'R3', facts: { payday: '2026-09-16' } }} />)
    expect(container).toBeEmptyDOMElement()
    rerender(<CheckVisual check={null} />)
    expect(container).toBeEmptyDOMElement()
  })
})
