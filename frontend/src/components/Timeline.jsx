import TierBadge from './TierBadge.jsx'
import TierLegend from './TierLegend.jsx'
import MonthlyChart from './MonthlyChart.jsx'
import { evidenceLabel, formatDate } from '../labels'

const monthNames = [
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

function monthLabel(key) {
  const [year, month] = key.split('-')
  return `${monthNames[Number(month) - 1] ?? month} ${year}`
}

function evidenceText(list) {
  return (list ?? []).map(evidenceLabel).join(', ')
}

function compareRecords(a, b) {
  if (a.paid_on !== b.paid_on) return a.paid_on < b.paid_on ? -1 : 1
  return a.record_id < b.record_id ? -1 : a.record_id > b.record_id ? 1 : 0
}

// Props: timeline = response of api.getTimeline (fixtures/timeline.json).
// Displays supplied numbers only; it computes no income figures.
export default function Timeline({ timeline }) {
  if (!timeline) {
    return (
      <section className="income-timeline">
        <p>Loading income timeline...</p>
      </section>
    )
  }

  const sources = timeline.sources ?? []
  const records = timeline.records ?? []
  const months = timeline.months ?? {}

  if (sources.length === 0 && records.length === 0) {
    return (
      <section className="income-timeline">
        <p>No income recorded yet. Add a document to build your timeline.</p>
      </section>
    )
  }

  const sourceLabel = new Map(sources.map((source) => [source.source_id, source.label]))
  const sortedRecords = [...records].sort(compareRecords)
  const monthKeys = Object.keys(months).sort()

  return (
    <section className="income-timeline">
      <h2>Income timeline</h2>
      <MonthlyChart months={months} />
      <TierLegend />
      <ul className="timeline-sources">
        {sources.map((source) => (
          <li key={source.source_id}>
            <span>{source.label}</span> <TierBadge tier={source.tier} variant="compact" />{' '}
            <span className="timeline-source-evidence">{evidenceText(source.evidence)}</span>
          </li>
        ))}
      </ul>
      {monthKeys.map((key) => {
        const month = months[key]
        const monthRecords = sortedRecords.filter((record) => record.paid_on?.startsWith(key))
        return (
          <details className="timeline-month" data-month={key} key={key}>
            <summary className="timeline-month-summary">
              <span className="timeline-month-name">{monthLabel(key)}</span>
              <span>
                Attested income (tiers A-C): <strong data-money>{dollars(month.net_cents)}</strong>
              </span>
              {month.self_reported_cents > 0 && (
                <span className="timeline-self-reported">
                  Self-reported cash (not attested): {dollars(month.self_reported_cents)}
                </span>
              )}
            </summary>
            {monthRecords.map((record) => (
              <div
                className="timeline-record"
                data-record-id={record.record_id}
                data-paid-on={record.paid_on}
                key={record.record_id}
              >
                <div>
                  {formatDate(record.paid_on)} · {sourceLabel.get(record.source_id) ?? record.source_id} ·{' '}
                  {dollars(record.net_cents)}
                </div>
                {record.original_currency && (
                  <div>
                    Original amount: {dollars(record.original_amount_cents)} {record.original_currency}
                  </div>
                )}
                <TierBadge tier={record.tier} variant="compact" />
                {record.tier === 'D' && <span> Self-reported (not attested)</span>}
                <div>Evidence: {evidenceText(record.evidence)}</div>
              </div>
            ))}
          </details>
        )
      })}
    </section>
  )
}
