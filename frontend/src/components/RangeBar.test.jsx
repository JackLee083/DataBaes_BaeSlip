import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import preview from '../../../fixtures/preview.json'
import RangeBar from './RangeBar.jsx'

const { monthly_income_range: range, monthly_median: median } = preview.attestation.summary
const money = (n) => '$' + n.toLocaleString('en-US')

const props = {
  low: range.low,
  high: range.high,
  median,
  lowLabel: money(range.low),
  highLabel: money(range.high),
  medianLabel: money(median),
}

describe('RangeBar', () => {
  it('labels low, high and median with the supplied formatted values', () => {
    render(<RangeBar {...props} />)
    expect(screen.getByText(`Low ${money(range.low)}`)).toBeInTheDocument()
    expect(screen.getByText(`High ${money(range.high)}`)).toBeInTheDocument()
    expect(screen.getByText(`Median ${money(median)}`)).toBeInTheDocument()
  })

  it('has an accessible description in words', () => {
    render(<RangeBar {...props} />)
    const img = screen.getByRole('img')
    expect(img).toHaveAttribute(
      'aria-label',
      `Monthly income range ${money(range.low)} to ${money(range.high)}, median ${money(median)}`,
    )
  })

  it('places the median marker proportionally inside the band', () => {
    const { container } = render(<RangeBar {...props} />)
    const marker = container.querySelector('[data-testid="range-median"]')
    const x = Number(marker.getAttribute('x1'))
    expect(x).toBeGreaterThan(0)
    expect(x).toBeLessThan(100)
  })

  it('can hide the median value text when it is shown next to the bar', () => {
    render(<RangeBar {...props} showMedianValue={false} />)
    expect(screen.queryByText(/\$2,700/)).toBeNull()
    expect(screen.getByText('Median')).toBeInTheDocument()
  })
})
