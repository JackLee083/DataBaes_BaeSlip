import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { tierShortLabel } from '../labels'
import TierLegend from './TierLegend'

const tiers = {
  A: 'Third party reported to government',
  B: 'Payer confirmed',
  C: 'Matched bank deposit',
  D: 'Self-reported only',
}

const count = (text, needle) => text.split(needle).length - 1

describe('TierLegend', () => {
  it('shows each tier definition exactly once with its letter and short label', () => {
    const { container } = render(<TierLegend />)

    expect(screen.getByText('What the tier letters mean')).toBeInTheDocument()
    for (const [tier, definition] of Object.entries(tiers)) {
      expect(count(container.textContent, definition)).toBe(1)
      expect(container).toHaveTextContent(`Tier ${tier}:`)
      expect(screen.getByText(tierShortLabel(tier))).toBeInTheDocument()
    }
  })

  it('lists four entries in order A, B, C, D inside the tier-legend dl', () => {
    const { container } = render(<TierLegend />)
    const dl = container.querySelector('dl')

    expect(dl).toHaveClass('tier-legend')
    const entries = Array.from(dl.children)
    expect(entries.map((el) => el.tagName)).toEqual(['DIV', 'DIV', 'DIV', 'DIV'])
    expect(entries.map((el) => el.querySelector('[data-tier]').getAttribute('data-tier'))).toEqual([
      'A',
      'B',
      'C',
      'D',
    ])
  })
})
