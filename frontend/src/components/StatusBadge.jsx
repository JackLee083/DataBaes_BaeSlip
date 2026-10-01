// StatusBadge: the verify page status.
// Shows symbol + text so the state never relies on colour alone.
// A failed signature overrides "valid" so a tampered record is never shown as Valid.
const STATES = {
  valid: { symbol: '✓', text: 'Valid' },
  expired: { symbol: '✗', text: 'Expired' },
  revoked: { symbol: '✗', text: 'Revoked' },
  not_found: { symbol: '✗', text: 'Not found' },
  loading: { symbol: '…', text: 'Checking' },
  invalid: { symbol: '✗', text: 'Signature invalid' },
}

export default function StatusBadge({ status, signatureValid }) {
  const requested = STATES[status] ? status : 'loading'
  const badSignature = signatureValid === false
  const state = badSignature && requested === 'valid' ? 'invalid' : requested
  const { symbol, text } = STATES[state]

  return (
    <>
      <div
        role="status"
        className={`status-badge status-badge--${state}`}
        data-status={state}
      >
        <span className="status-badge__symbol" aria-hidden="true">{symbol}</span>
        <span className="status-badge__text">{text}</span>
      </div>
      {badSignature && (
        <p className="signature-warning">
          The signature does not match the issuer's key, so the contents may have been
          changed and must not be trusted.
        </p>
      )}
    </>
  )
}
