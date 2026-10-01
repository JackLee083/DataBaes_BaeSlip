// BaeSlip standard spec page (owner: web-verify, ticket F6). Static and read-only.
import { keysUrl } from '../api.js'
import schema from '../../../schema/attestation.schema.json'

const SPEC_VERSION = '0.1'

const TIERS = [
  {
    letter: 'A',
    definition: 'Reported to the government by a third party',
    example: 'STP income statement, Notice of Assessment',
  },
  {
    letter: 'B',
    definition: 'Confirmed by the payer',
    example: 'Platform earnings statement, invoice confirmed by the payer',
  },
  {
    letter: 'C',
    definition: 'Matched to a bank deposit',
    example: 'A claimed income found as a matching bank deposit',
  },
  {
    letter: 'D',
    definition: 'Self-reported only',
    example: 'Own records of hours, cash income',
  },
]

// [field, rental, lending]
const SCOPE_ROWS = [
  ['Source label, type and tier', true, true],
  ['Monthly income range and median', true, true],
  ['Coverage, period, issue date and expiry', true, true],
  ['Monthly series', false, true],
  ['Per-source monthly income', false, true],
  ['Forbidden list (see below)', false, false],
]

const FORBIDDEN = [
  'Hours worked',
  'Visa status',
  'Individual transactions',
  'Integrity-check results',
]

export default function Spec() {
  return (
    <main className="spec-page">
      <h1>BaeSlip standard</h1>
      <p>Version {SPEC_VERSION}</p>
      <p>
        BaeSlip is an open standard for income attestations. Any issuer that implements it can
        issue one. Every line of an attestation names its evidence. The worker starts every share
        and can revoke it.
      </p>

      <section className="spec-tiers">
        <h2>Credibility tiers</h2>
        <table>
          <thead>
            <tr>
              <th scope="col">Tier</th>
              <th scope="col">Definition</th>
              <th scope="col">Example evidence</th>
            </tr>
          </thead>
          <tbody>
            {TIERS.map((t) => (
              <tr key={t.letter}>
                <td>{t.letter}</td>
                <td>{t.definition}</td>
                <td>{t.example}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <ul>
          <li>A record&apos;s tier is its strongest evidence.</li>
          <li>
            A source&apos;s tier is its weakest month (conservative: we do not pretend to know
            more).
          </li>
        </ul>
      </section>

      <section className="spec-scope">
        <h2>Scope</h2>
        <p>What an attestation discloses depends on its scope. Lending is specified only, not implemented.</p>
        <table>
          <thead>
            <tr>
              <th scope="col">Field</th>
              <th scope="col">Rental</th>
              <th scope="col">Lending</th>
            </tr>
          </thead>
          <tbody>
            {SCOPE_ROWS.map(([field, rental, lending]) => (
              <tr key={field}>
                <th scope="row">{field}</th>
                <td>{rental ? 'Yes' : 'No'}</td>
                <td>{lending ? 'Yes' : 'No'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="spec-forbidden">
        <h2>Never in an attestation</h2>
        <p>Only income is disclosed, never work details.</p>
        <ul>
          {FORBIDDEN.map((f) => (
            <li key={f}>{f}</li>
          ))}
        </ul>
        <p>Integrity checks are shown only to the worker.</p>
      </section>

      <section className="spec-signing">
        <h2>Signing and status</h2>
        <p>
          An attestation is signed with Ed25519 over the canonical JSON (keys sorted, no
          whitespace, UTF-8) of everything except the signature field.
        </p>
        <p>
          Status (valid, expired or revoked) is reported live by the issuer and is not signed, so
          revoking needs no re-signing.
        </p>
        <p>Attestations expire 30 days after issue.</p>
        <p>
          <a href={keysUrl()}>Issuer public keys</a>
        </p>
      </section>

      <section className="spec-schema">
        <h2>JSON Schema (draft 2020-12)</h2>
        <pre>
          <code>{JSON.stringify(schema, null, 2)}</code>
        </pre>
      </section>
    </main>
  )
}
