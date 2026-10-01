import { formatDate } from '../labels.js'

const money = new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
  minimumFractionDigits: 2,
})

const WIDTH = 320
const PAD = 8
const TRACK = WIDTH - PAD * 2

const isNumber = (value) => typeof value === 'number' && Number.isFinite(value)
const dayNumber = (iso) => Date.parse(`${iso}T00:00:00Z`) / 86400000

function Frame({ height, label, children }) {
  return (
    <svg
      className="check-visual"
      role="img"
      aria-label={label}
      viewBox={`0 0 ${WIDTH} ${height}`}
      preserveAspectRatio="xMinYMin meet"
    >
      {children}
    </svg>
  )
}

function MoneyBars({ check }) {
  const { expected_cents: expected, actual_cents: paid } = check
  if (!isNumber(expected) || !isNumber(paid)) return null

  const top = Math.max(expected, paid)
  if (top <= 0) return null
  const rows = [
    ['Expected', expected, 'check-visual__bar--expected'],
    ['Paid', paid, 'check-visual__bar--actual'],
  ]

  return (
    <Frame
      height={70}
      label={`Expected ${money.format(expected / 100)}, paid ${money.format(paid / 100)}`}
    >
      {rows.map(([name, cents, className], index) => (
        <g key={name} transform={`translate(${PAD} ${index * 34 + 2})`}>
          <text className="check-visual__text" y="12">{`${name} ${money.format(cents / 100)}`}</text>
          <rect className="check-visual__track" y="17" width={TRACK} height="10" rx="3" />
          <rect className={className} y="17" width={Math.max(2, (cents / top) * TRACK)} height="10" rx="3" />
        </g>
      ))}
    </Frame>
  )
}

function DateLine({ check }) {
  const { payday, deadline, received_on: received } = check.facts ?? {}
  if (!payday || !deadline || !received) return null

  const start = dayNumber(payday)
  const end = Math.max(dayNumber(deadline), dayNumber(received))
  if (![start, end].every(Number.isFinite) || end <= start) return null

  const x = (iso) => PAD + 4 + ((dayNumber(iso) - start) / (end - start)) * (TRACK - 8)
  const late = dayNumber(received) > dayNumber(deadline)
  const lineY = 34

  return (
    <Frame
      height={72}
      label={`Payday ${formatDate(payday)}, deadline ${formatDate(deadline)}, super received ${formatDate(received)}${late ? ', after the deadline' : ''}`}
    >
      <line className="check-visual__axis" x1={PAD} x2={WIDTH - PAD} y1={lineY} y2={lineY} />
      {late && (
        <line className="check-visual__late" x1={x(deadline)} x2={x(received)} y1={lineY} y2={lineY} />
      )}
      <circle className="check-visual__dot" cx={x(payday)} cy={lineY} r="5" />
      <line className="check-visual__marker" x1={x(deadline)} x2={x(deadline)} y1={lineY - 9} y2={lineY + 9} />
      <rect
        className={late ? 'check-visual__dot check-visual__dot--late' : 'check-visual__dot'}
        x={x(received) - 5}
        y={lineY - 5}
        width="10"
        height="10"
        transform={`rotate(45 ${x(received)} ${lineY})`}
      />
      <text className="check-visual__text" x={PAD} y="16">{`Payday ${formatDate(payday)}`}</text>
      <text className="check-visual__text" x={WIDTH - PAD} y="16" textAnchor="end">
        {`Received ${formatDate(received)}${late ? ' (late)' : ''}`}
      </text>
      <text className="check-visual__text" x={x(deadline)} y="60" textAnchor="middle">
        {`Deadline ${formatDate(deadline)}`}
      </text>
    </Frame>
  )
}

function HoursGauge({ check }) {
  const { total_hours: total, limit_hours: limit, warn_hours: warn } = check.facts ?? {}
  if (!isNumber(total) || !isNumber(limit)) return null

  const scaleMax = Math.max(total, limit, isNumber(warn) ? warn : 0) * 1.1
  if (scaleMax <= 0) return null
  const x = (hours) => PAD + (hours / scaleMax) * TRACK
  const over = total > limit

  return (
    <Frame height={70} label={`${total} of ${limit} hours${over ? ', over the limit' : ''}`}>
      <rect className="check-visual__track" x={PAD} y="26" width={TRACK} height="14" rx="3" />
      <rect
        className={over ? 'check-visual__bar--actual' : 'check-visual__bar--expected'}
        x={PAD}
        y="26"
        width={Math.max(2, (total / scaleMax) * TRACK)}
        height="14"
        rx="3"
      />
      {isNumber(warn) && (
        <>
          <line className="check-visual__marker check-visual__marker--warn" x1={x(warn)} x2={x(warn)} y1="22" y2="46" />
          <text className="check-visual__text" x={x(warn) - 3} y="60" textAnchor="end">{`${warn} h warn`}</text>
        </>
      )}
      <line className="check-visual__marker" x1={x(limit)} x2={x(limit)} y1="22" y2="46" />
      <text className="check-visual__text" x={Math.min(x(limit) + 3, WIDTH - PAD)} y="16" textAnchor="end">{`${limit} h limit`}</text>
      <text className="check-visual__text check-visual__text--strong" x={PAD} y="16">{`${total} h`}</text>
    </Frame>
  )
}

export default function CheckVisual({ check }) {
  if (!check) return null
  if (check.rule === 'R1' || check.rule === 'R2') return <MoneyBars check={check} />
  if (check.rule === 'R3') return <DateLine check={check} />
  if (check.rule === 'R4') return <HoursGauge check={check} />
  return null
}
