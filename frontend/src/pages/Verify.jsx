// Landlord verify page for /v/:id (owner: web-verify, ticket F2).
// Shows only the whitelisted rental-scope fields (MVP 4.3); revoked and
// not-found responses never render income figures or sources.
import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { verifyAttestation, keysUrl } from '../api.js'
import StatusBadge from '../components/StatusBadge.jsx'
import TierBadge from '../components/TierBadge.jsx'
import RangeBar from '../components/RangeBar.jsx'
import { evidenceLabel, formatDate, formatDateRange } from '../labels.js'
import '../styles/verify.css'

const TYPE_LABELS = {
  employment: 'Employment',
  platform: 'Platform work',
  contract: 'Contract',
  overseas_contract: 'Overseas contract',
  cash: 'Cash',
}

function AttestationDetails({ attestation }) {
  const { subject, period, summary, sources, issuer } = attestation
  const money = new Intl.NumberFormat('en-AU', {
    style: 'currency',
    currency: summary.currency,
    maximumFractionDigits: 0,
  })
  const { low, high } = summary.monthly_income_range
  const { months_with_data: have, months_in_period: total } = summary.coverage

  return (
    <>
      <section className="verify-summary">
        <h2>{`Income for ${subject.display_name}`}</h2>
        <p>{formatDateRange(period.start, period.end)}</p>
        <p>
          Monthly income range:{' '}
          <strong>{`${money.format(low)}–${money.format(high)}`}</strong>
        </p>
        <p>
          Monthly median: <strong>{money.format(summary.monthly_median)}</strong>
        </p>
        <RangeBar
          low={low}
          high={high}
          median={summary.monthly_median}
          lowLabel={money.format(low)}
          highLabel={money.format(high)}
          medianLabel={money.format(summary.monthly_median)}
        />
        <p>{`${have} of ${total} months with data`}</p>
      </section>

      <section className="verify-sources">
        <h2>Sources</h2>
        <ul>
          {sources.map((source, i) => (
            <li className="verify-source" key={`${source.label}-${i}`}>
              <span className="verify-source__label">{source.label}</span>
              <span className="verify-source__type">{TYPE_LABELS[source.type] || source.type}</span>
              <span className="verify-source__tier"><TierBadge tier={source.tier} /></span>
              <span className="verify-source__evidence">
                {`Evidence: ${source.evidence.map(evidenceLabel).join(', ')}`}
              </span>
            </li>
          ))}
        </ul>
      </section>

      <section className="verify-issuer">
        <p>{`Issued by ${issuer.name}`}</p>
        <p>{`Issued ${formatDate(attestation.issued_at)}, expires ${formatDate(attestation.expires_at)}`}</p>
        <p>
          <a href={keysUrl()}>Check the signature yourself: issuer public keys</a>
        </p>
      </section>
    </>
  )
}

export default function Verify() {
  const { id } = useParams()
  const [attempt, setAttempt] = useState(0)
  const [result, setResult] = useState(null)
  const key = `${id}#${attempt}`

  useEffect(() => {
    let ignore = false
    verifyAttestation(id).then(
      (res) => {
        if (!ignore) setResult({ key, res })
      },
      () => {
        if (!ignore) setResult({ key, error: true })
      },
    )
    return () => {
      ignore = true
    }
  }, [id, key])

  const retry = useCallback(() => setAttempt((n) => n + 1), [])
  // A result for an older id/attempt counts as still loading.
  const current = result && result.key === key ? result : null
  const phase = !current ? 'loading' : current.error ? 'error' : 'done'
  const res = current && current.res

  return (
    <main className="verify-page">
      <h1>Verify income attestation</h1>
      <p>{`Attestation ID: ${id}`}</p>

      {phase === 'loading' && <StatusBadge status="loading" />}

      {phase === 'error' && (
        <>
          <p role="alert">Could not reach the issuer to check this attestation.</p>
          <button type="button" onClick={retry}>Try again</button>
        </>
      )}

      {phase === 'done' && (
        <>
          <StatusBadge status={res.status} signatureValid={res.signature_valid} />
          {res.status === 'expired' && (
            <p>This attestation has expired; the figures may be out of date.</p>
          )}
          {res.status === 'revoked' && (
            <>
              <p>The person who shared this attestation has withdrawn it.</p>
              {res.revoked_at && (
                <p>{`Revoked at ${res.revoked_at.slice(0, 10)} ${res.revoked_at.slice(11, 16)}`}</p>
              )}
            </>
          )}
          {res.status === 'not_found' && (
            <p>No attestation with this ID exists at this issuer.</p>
          )}
          {(res.status === 'valid' || res.status === 'expired') && res.attestation && (
            <AttestationDetails attestation={res.attestation} />
          )}
        </>
      )}
    </main>
  )
}
