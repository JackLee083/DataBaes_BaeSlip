import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import timeline from '../../../fixtures/timeline.json'
import MonthlyChart from './MonthlyChart.jsx'

describe('MonthlyChart', () => {
  it('renders one bar per month with the supplied net income labelled', () => {
    const { container } = render(<MonthlyChart months={timeline.months} />)
    const bars = container.querySelectorAll('[data-month-bar]')
    expect(bars).toHaveLength(6)
    const labels = [...bars].map((b) => b.getAttribute('data-month-bar'))
    expect(labels).toEqual(['2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09'])
    const chart = screen.getByRole('img')
    expect(within(chart).getByText('Apr')).toBeInTheDocument()
    expect(within(chart).getByText('$2,450')).toBeInTheDocument()
    expect(within(chart).getByText('$2,300')).toBeInTheDocument()
    expect(within(chart).getByText('$2,620')).toBeInTheDocument()
    expect(within(chart).getByText('$2,780')).toBeInTheDocument()
  })

  it('draws a hatched cash segment only for months with self-reported cash', () => {
    const { container } = render(<MonthlyChart months={timeline.months} />)
    const cash = container.querySelectorAll('[data-cash-bar]')
    expect(cash).toHaveLength(1)
    expect(cash[0].getAttribute('data-cash-bar')).toBe('2026-08')
    expect(within(screen.getByRole('img')).getByText('$60 cash, not attested')).toBeInTheDocument()
  })

  it('includes a legend and an accessible summary', () => {
    render(<MonthlyChart months={timeline.months} />)
    expect(screen.getByText('Attested income (tiers A-C)')).toBeInTheDocument()
    expect(screen.getByText('Self-reported cash (not attested)')).toBeInTheDocument()
    expect(screen.getByRole('img').getAttribute('aria-label')).toMatch(/April: \$2,450/)
  })

  it('renders nothing without months', () => {
    const { container } = render(<MonthlyChart months={{}} />)
    expect(container.firstChild).toBeNull()
  })
})
