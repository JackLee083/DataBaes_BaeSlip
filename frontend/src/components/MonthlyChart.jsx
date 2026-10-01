import { useId } from 'react'
import '../styles/charts.css'

const SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const LONG = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

// Formats supplied cents as dollars; whole-dollar amounts drop the decimals.
function dollars(cents) {
  const value = (cents ?? 0) / 100
  const whole = Number.isInteger(value)
  return `$${value.toLocaleString('en-US', {
    minimumFractionDigits: whole ? 0 : 2,
    maximumFractionDigits: 2,
  })}`
}

const W = 360
const TOP = 30
const PLOT_H = 110
const BASE = TOP + PLOT_H
const H = BASE + 40
const MIN_CASH_H = 6

const monthIndex = (key) => Number(key.split('-')[1]) - 1

// Vertical bars from the supplied timeline.months. Heights only scale the
// supplied cents; every printed amount is a supplied value, formatted.
export default function MonthlyChart({ months }) {
  const patternId = 'cash-hatch-' + useId().replace(/[^a-zA-Z0-9]/g, '')
  const keys = Object.keys(months ?? {}).sort()
  if (keys.length === 0) return null

  const scaleMax = Math.max(...keys.map((k) => (months[k].net_cents ?? 0) + (months[k].self_reported_cents ?? 0)), 1)
  const slot = W / keys.length
  const barW = Math.min(slot * 0.6, 44)
  const summary = keys
    .map((k) => `${LONG[monthIndex(k)] ?? k}: ${dollars(months[k].net_cents)}`)
    .join('; ')

  return (
    <div className="monthly-chart">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Attested monthly income (tiers A-C). ${summary}`}
      >
        <defs>
          <pattern id={patternId} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <rect width="5" height="5" fill="var(--tier-d-bg)" />
            <line x1="0" y1="0" x2="0" y2="5" stroke="var(--text)" strokeWidth="2" />
          </pattern>
        </defs>
        <line className="monthly-chart__baseline" x1="0" x2={W} y1={BASE} y2={BASE} />
        {keys.map((key, i) => {
          const m = months[key]
          const cx = slot * i + slot / 2
          const netH = ((m.net_cents ?? 0) / scaleMax) * PLOT_H
          const cash = m.self_reported_cents ?? 0
          const cashH = cash > 0 ? Math.max(MIN_CASH_H, (cash / scaleMax) * PLOT_H) : 0
          const label = SHORT[monthIndex(key)] ?? key
          // Label sits above the tallest possible bar so it never overlaps a neighbour.
          const cashX = Math.min(W - 70, Math.max(70, cx))
          return (
            <g key={key}>
              <rect
                className="monthly-chart__bar"
                data-month-bar={key}
                x={cx - barW / 2}
                y={BASE - netH}
                width={barW}
                height={netH}
              />
              {cash > 0 && (
                <>
                  <rect
                    className="monthly-chart__cash"
                    data-cash-bar={key}
                    x={cx - barW / 2}
                    y={BASE - netH - cashH}
                    width={barW}
                    height={cashH}
                    fill={`url(#${patternId})`}
                  />
                  <text
                    className="monthly-chart__cash-label"
                    x={cashX}
                    y={TOP - 12}
                    textAnchor="middle"
                  >
                    {`${dollars(cash)} cash, not attested`}
                  </text>
                </>
              )}
              <text className="monthly-chart__value" x={cx} y={BASE + 16} textAnchor="middle">
                {dollars(m.net_cents)}
              </text>
              <text x={cx} y={BASE + 32} textAnchor="middle">
                {label}
              </text>
            </g>
          )
        })}
      </svg>
      <ul className="monthly-chart__legend">
        <li>
          <span className="monthly-chart__swatch" aria-hidden="true" />
          <span>Attested income (tiers A-C)</span>
        </li>
        <li>
          <span className="monthly-chart__swatch monthly-chart__swatch--cash" aria-hidden="true" />
          <span>Self-reported cash (not attested)</span>
        </li>
      </ul>
    </div>
  )
}
