import { tierShortLabel } from '../labels'

const TIER_DEFINITIONS = {
  A: 'Third party reported to government',
  B: 'Payer confirmed',
  C: 'Matched bank deposit',
  D: 'Self-reported only',
}

// Also used on the verify page.
// Props: tier = "A" | "B" | "C" | "D"; variant = "compact" for letter + short label only.
export default function TierBadge({ tier, variant }) {
  const definition = TIER_DEFINITIONS[tier]

  if (variant === 'compact') {
    const full = `Tier ${tier}: ${definition}`
    return (
      <span
        className="tier-badge tier-badge--compact"
        data-tier={tier}
        aria-label={full}
        title={full}
      >
        <strong>{tier}</strong> {tierShortLabel(tier)}
      </span>
    )
  }

  return (
    <span className="tier-badge" data-tier={tier} aria-label={`Tier ${tier}: ${definition}`}>
      Tier {tier}: {definition}
    </span>
  )
}
