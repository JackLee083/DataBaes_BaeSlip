import { useCallback, useEffect, useState } from 'react'
import TierBadge from './TierBadge.jsx'
import RangeBar from './RangeBar.jsx'
import { previewAttestation } from '../api.js'

// Income summary for /app. Loads the attestation preview on its own and shows
// the supplied summary figures; it formats numbers but never computes them.
function useLoad(load) {
  const [state, setState] = useState({ status: 'loading', data: null })
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let active = true
    load()
      .then((data) => {
        if (active) setState({ status: 'ready', data })
      })
      .catch(() => {
        if (active) setState({ status: 'error', data: null })
      })
    return () => {
      active = false
    }
  }, [load, attempt])

  const retry = useCallback(() => {
    setState({ status: 'loading', data: null })
    setAttempt((n) => n + 1)
  }, [])

  return [state, retry]
}

const loadPreview = () => previewAttestation('mei', 'rental')
const money = (n) => '$' + n.toLocaleString('en-US')

export default function IncomeSummary({ onCreateProof }) {
  const [preview, retry] = useLoad(loadPreview)
  const attestation = preview.data?.attestation
  const summary = attestation?.summary
  const sources = attestation?.sources ?? []

  return (
    <section className="income-summary" aria-labelledby="income-summary-heading">
      <h2 id="income-summary-heading">Income summary</h2>

      {preview.status === 'loading' && <p role="status">Loading income summary...</p>}
      {preview.status === 'error' && (
        <div role="alert">
          <p>Unable to load the income summary.</p>
          <button type="button" onClick={retry}>
            Retry
          </button>
        </div>
      )}
      {preview.status === 'ready' && summary && (
        <>
          <dl className="income-summary-figures">
            <div>
              <dt>Monthly income range</dt>
              <dd>
                <span className="income-summary-range" data-money>
                  {`${money(summary.monthly_income_range.low)}–${money(summary.monthly_income_range.high)}`}
                </span>{' '}
                <span className="income-summary-unit">per month ({summary.currency})</span>
              </dd>
            </div>
            <div>
              <dt>Median month</dt>
              <dd>
                <span data-money>{money(summary.monthly_median)}</span>
              </dd>
            </div>
            <div>
              <dt>Coverage</dt>
              <dd>
                <span data-money>
                  {`${summary.coverage.months_with_data} of ${summary.coverage.months_in_period} months with data`}
                </span>
              </dd>
            </div>
          </dl>
          <RangeBar
            low={summary.monthly_income_range.low}
            high={summary.monthly_income_range.high}
            median={summary.monthly_median}
            lowLabel={money(summary.monthly_income_range.low)}
            highLabel={money(summary.monthly_income_range.high)}
            medianLabel={money(summary.monthly_median)}
            showMedianValue={false}
          />
          <ul className="income-summary-sources">
            {sources.map((source, i) => (
              <li key={`${source.label}-${i}`}>
                <span>{source.label}</span> <TierBadge tier={source.tier} variant="compact" />
              </li>
            ))}
          </ul>
        </>
      )}

      <button type="button" className="primary-action" onClick={onCreateProof}>
        Create a rental proof
      </button>
    </section>
  )
}
