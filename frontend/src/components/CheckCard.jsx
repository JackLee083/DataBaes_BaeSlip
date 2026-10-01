import { useState } from 'react'
import { explainCheck } from '../api.js'
import CheckVisual from './CheckVisual.jsx'
import { evidenceLabel, formatDate, formatDateRange, ruleLabel, severityLabel } from '../labels.js'
import '../styles/checks.css'

const money = new Intl.NumberFormat('en-AU', {
  style: 'currency',
  currency: 'AUD',
  minimumFractionDigits: 2,
})

const factLabels = {
  source_id: 'Source',
  source_label: 'Source',
  hours: 'Hours',
  min_hourly_cents: 'Minimum hourly rate',
  effective_hourly_cents: 'Effective hourly rate',
  gross_cents: 'Gross pay',
  actual_basis: 'Actual basis',
  paid_on: 'Paid on',
  note: 'Note',
  engaged_minutes: 'Engaged minutes',
  engaged_hours: 'Engaged hours',
  min_per_engaged_hour_cents: 'Minimum per engaged hour',
  payout_cents: 'Payout',
  payday: 'Payday',
  deadline: 'Deadline',
  business_days: 'Business days allowed',
  received_on: 'Received on',
  business_days_late: 'Business days late',
  window_start: 'Window start',
  window_end: 'Window end',
  total_hours: 'Total hours',
  limit_hours: 'Limit hours',
  warn_hours: 'Warning hours',
  status: 'Status',
  counts_platform_online_time: 'Includes platform online time',
  period_start: 'Period start',
  period_end: 'Period end',
  verification_status: 'Verified by',
  award_limitation: 'Award note',
  as_of: 'As of',
}

const verificationLabels = {
  stp_income_statement: 'Government income statement (STP)',
  matched_bank_deposit: 'Matched bank deposit',
  unmatched_bank_deposit: 'Unmatched bank deposit',
}

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/
const CODE = /^[a-z]+(_[a-z]+)+$/

function humanize(code) {
  return code.replaceAll('_', ' ').replace(/^./, (letter) => letter.toUpperCase())
}

const severityIcons = {
  info: 'ℹ',
  review: '⚠',
  warning: '▲',
}

function labelFor(key) {
  return factLabels[key] ?? humanize(key)
}

function valueFor(key, value) {
  if (key.endsWith('_cents')) return money.format(value / 100)
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (key === 'actual_basis') return evidenceLabel(value)
  if (key === 'verification_status') return verificationLabels[value] ?? humanize(value)
  // Any other date or snake_case code the backend adds is still shown readably.
  if (typeof value === 'string' && ISO_DATE.test(value)) return formatDate(value)
  if (typeof value === 'string' && CODE.test(value)) return humanize(value)
  return String(value)
}

function MonetaryValues({ check }) {
  const values = [
    ['Expected', check.expected_cents],
    ['Actual', check.actual_cents],
  ].filter(([, value]) => value !== null && value !== undefined)

  if (values.length === 0) return null

  return (
    <dl className="check-money">
      {values.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd className="money data-money">{money.format(value / 100)}</dd>
        </div>
      ))}
    </dl>
  )
}

function KeyFigure({ check }) {
  if (check.rule === 'R1' || check.rule === 'R2') {
    return <p className="check-card__figure data-money">Difference {money.format(check.difference_cents / 100)}</p>
  }

  if (check.rule === 'R3') {
    const days = check.facts?.business_days_late
    return <p className="check-card__figure">{days} business day{days === 1 ? '' : 's'} late</p>
  }

  if (check.rule === 'R4') {
    return <p className="check-card__figure">{check.facts?.total_hours} of {check.facts?.limit_hours} hours</p>
  }

  return null
}

function Facts({ check }) {
  const omitted = check.rule === 'R3' ? new Set(['super_amount_cents']) : new Set()
  const facts = Object.entries(check.facts ?? {}).filter(([key]) => {
    if (key === 'limitations' || key === 'planned_shifts' || omitted.has(key)) return false
    return key !== 'source_id' || !check.facts?.source_label
  })
  const limitations = check.facts?.limitations ?? []
  const plannedShifts = check.facts?.planned_shifts ?? []

  return (
    <section className="check-facts" aria-label="Calculation inputs and facts">
      <h3>Calculation inputs</h3>
      <dl>
        {facts.map(([key, value]) => (
          <div key={key}>
            <dt>{labelFor(key)}</dt>
            <dd className={key.endsWith('_cents') ? 'money data-money' : undefined}>{valueFor(key, value)}</dd>
          </div>
        ))}
      </dl>
      {limitations.length > 0 && (
        <>
          <h3>Limitations</h3>
          <ul>{limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        </>
      )}
      {plannedShifts.length > 0 && (
        <>
          <h3>Planned shifts</h3>
          <ul>
            {plannedShifts.map((shift) => (
              <li key={`${shift.date}-${shift.source_id}-${shift.hours}`}>
                {formatDate(shift.date)}: {shift.hours} hours
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  )
}

function List({ title, items }) {
  if (!items?.length) return null
  return (
    <section>
      <h3>{title}</h3>
      <ul>{items.map((item) => <li key={item}>{item}</li>)}</ul>
    </section>
  )
}

function LoadedCheckCard({ check, language }) {
  const [explanation, setExplanation] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(false)
  const [shown, setShown] = useState(false)
  const explanationId = `explanation-${check.check_id}`

  async function requestExplanation() {
    if (isLoading) return
    setIsLoading(true)
    setError(false)
    try {
      setExplanation(await explainCheck(check.check_id, language))
      setShown(true)
    } catch {
      setError(true)
    } finally {
      setIsLoading(false)
    }
  }

  function toggleExplanation() {
    if (explanation) setShown((visible) => !visible)
    else requestExplanation()
  }

  return (
    <article className={`check-card check-card--${check.severity}`}>
      <header className="check-card__summary">
        <p className="check-card__rule">{ruleLabel(check.rule)}</p>
        <h2>{check.title}</h2>
        <p className="check-card__severity">
          <span className="check-card__severity-icon" aria-hidden="true">{severityIcons[check.severity] ?? '•'}</span>
          {severityLabel(check.severity)}
        </p>
        <KeyFigure check={check} />
        <CheckVisual check={check} />
        <p className="check-card__period">{formatDateRange(check.period_start, check.period_end)}</p>
      </header>
      <button
        type="button"
        onClick={toggleExplanation}
        disabled={isLoading}
        aria-expanded={shown}
        aria-controls={explanationId}
      >
        {shown ? 'Hide explanation' : 'Explain in my language'}
      </button>
      <details className="check-card__details">
        <summary>Details</summary>
        <MonetaryValues check={check} />
        <Facts check={check} />
        <List title="Possible explanations" items={check.possible_explanations} />
        <List title="Next steps" items={check.next_steps} />
      </details>
      {isLoading && <p role="status">Loading explanation…</p>}
      {error && (
        <div role="alert">
          <p>Unable to load an explanation.</p>
          <button type="button" onClick={requestExplanation} disabled={isLoading}>Retry explanation</button>
        </div>
      )}
      {explanation && (
        <section id={explanationId} className="check-explanation" aria-live="polite" hidden={!shown}>
          <h3>{explanation.source === 'template' ? 'Standard explanation' : 'AI explanation'}</h3>
          <p lang={language}>{explanation.text}</p>
        </section>
      )}
    </article>
  )
}

export default function CheckCard({ check, language = 'en' }) {
  if (!check) return null

  return <LoadedCheckCard check={check} language={language} />
}
