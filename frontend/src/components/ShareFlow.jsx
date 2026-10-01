// ShareFlow: preview -> create -> QR -> revoke.
// Props: workerId (default "mei"), scope (default "rental")
import { useState } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { createAttestation, previewAttestation, revokeAttestation } from '../api.js'

const REASON_TEXT = { never: 'never shared', scope: 'not in rental scope' }

export default function ShareFlow({ workerId = 'mei', scope = 'rental' }) {
  const [preview, setPreview] = useState(null) // cached; toggling never refetches
  const [previewOpen, setPreviewOpen] = useState(false)
  const [issued, setIssued] = useState(null) // IssueResponse; its attestation_id is what revoke needs
  const [revoked, setRevoked] = useState(null) // { revokedAt, verifyUrl } once the link is revoked
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function run(call, onDone, ...args) {
    setLoading(true)
    setError(null)
    try {
      onDone(await call(...args))
    } catch (err) {
      setError(err?.message || 'Something went wrong')
    } finally {
      setLoading(false)
    }
  }

  function onPreviewed(res) {
    setPreview(res)
    setPreviewOpen(true)
  }

  function togglePreview() {
    if (preview) setPreviewOpen((open) => !open)
    else run(previewAttestation, onPreviewed, workerId, scope)
  }

  function onCreated(res) {
    setRevoked(null)
    setIssued(res)
  }

  function onRevoked(res) {
    setRevoked({ revokedAt: res.revoked_at, verifyUrl: issued.verify_url })
    setIssued(null)
  }

  return (
    <section className="share-flow">
      <h2>Share a rental attestation</h2>
      <button
        type="button"
        disabled={loading}
        aria-expanded={previewOpen}
        aria-controls="share-preview"
        onClick={togglePreview}
      >
        {previewOpen ? 'Hide preview' : 'Preview what will be shared'}
      </button>
      {preview && previewOpen && (
        <div id="share-preview">
          <div className="share-preview-included">
            <h3>Will be shared</h3>
            <ul>
              {preview.included.map((item) => (
                <li key={item.key}>{item.label}</li>
              ))}
            </ul>
          </div>
          <div className="share-preview-excluded">
            <h3>Will not be shared</h3>
            <ul>
              {preview.excluded.map((item) => (
                <li key={item.key}>
                  {item.label} <span>({REASON_TEXT[item.reason] ?? item.reason})</span>
                </li>
              ))}
            </ul>
          </div>
          <button
            type="button"
            disabled={loading}
            onClick={() => run(createAttestation, onCreated, workerId, scope)}
          >
            Create rental attestation
          </button>
        </div>
      )}
      {loading && <p>Loading…</p>}
      {error && <p role="alert">{error}</p>}
      {issued && (
        <div className="share-qr">
          <QRCodeSVG value={issued.verify_url} title="QR code for the verify link" />
          <p>
            <a href={issued.verify_url}>{issued.verify_url}</a>
          </p>
          <p>Valid until {issued.attestation.expires_at.slice(0, 10)}</p>
          <button
            type="button"
            disabled={loading}
            onClick={() =>
              run(revokeAttestation, onRevoked, issued.attestation.attestation_id)
            }
          >
            Revoke
          </button>
        </div>
      )}
      {revoked && (
        <div className="share-revoked">
          <p>Revoked at {revoked.revokedAt.slice(0, 10) + ' ' + revoked.revokedAt.slice(11, 16)}</p>
          <p>{revoked.verifyUrl}</p>
          <p>Anyone who opens the link now sees “Revoked”.</p>
        </div>
      )}
    </section>
  )
}
