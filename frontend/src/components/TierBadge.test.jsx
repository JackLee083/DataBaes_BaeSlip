import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { tierShortLabel } from '../labels'
import TierBadge from './TierBadge'

const tiers = {
  A: 'Third party reported to government',
  B: 'Payer confirmed',
  C: 'Matched bank deposit',
  D: 'Self-reported only',
}

describe('TierBadge', () => {
  it('each tier exposes its letter and evidence definition without relying on color', () => {
    render(
      <>
        {Object.keys(tiers).map((tier) => (
          <TierBadge key={tier} tier={tier} />
        ))}
      </>,
    )

    for (const [tier, definition] of Object.entries(tiers)) {
      const badge = screen.getByLabelText(`Tier ${tier}: ${definition}`)

      expect(badge).toHaveTextContent(`Tier ${tier}`)
      expect(badge).toHaveTextContent(definition)
      expect(badge).toHaveClass('tier-badge')
      expect(badge).toHaveAttribute('data-tier', tier)
    }
  })

  it('compact variant shows the letter and short label, full definition as accessible name and title', () => {
    render(
      <>
        {Object.keys(tiers).map((tier) => (
          <TierBadge key={tier} tier={tier} variant="compact" />
        ))}
      </>,
    )

    for (const [tier, definition] of Object.entries(tiers)) {
      const badge = screen.getByLabelText(`Tier ${tier}: ${definition}`)

      expect(badge).toHaveClass('tier-badge')
      expect(badge).toHaveClass('tier-badge--compact')
      expect(badge).toHaveAttribute('data-tier', tier)
      expect(badge).toHaveAttribute('title', `Tier ${tier}: ${definition}`)
      expect(badge.textContent).toBe(`${tier} ${tierShortLabel(tier)}`)
      expect(badge.textContent).not.toContain(definition)
    }
    expect(screen.getByLabelText('Tier A: Third party reported to government').textContent).toBe(
      'A Gov-reported',
    )
  })

  it('default variant output is unchanged', () => {
    const { container } = render(<TierBadge tier="A" />)

    expect(container.innerHTML).toBe(
      '<span class="tier-badge" data-tier="A" aria-label="Tier A: Third party reported to government">Tier A: Third party reported to government</span>',
    )
  })
})
