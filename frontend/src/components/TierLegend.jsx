import TierBadge from './TierBadge.jsx'
import { tierShortLabel } from '../labels'

const TIERS = ['A', 'B', 'C', 'D']

// One legend for the compact badges on /app: each short label next to the full default badge,
// so every full definition appears once on the page.
export default function TierLegend() {
  return (
    <div className="tier-legend-block">
      <h3 id="tier-legend-heading">What the tier letters mean</h3>
      <dl className="tier-legend" aria-labelledby="tier-legend-heading">
        {TIERS.map((tier) => (
          <div key={tier}>
            <dt>{tierShortLabel(tier)}</dt>
            <dd>
              <TierBadge tier={tier} />
            </dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
