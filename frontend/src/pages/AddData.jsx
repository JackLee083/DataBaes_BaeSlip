import { useState } from 'react'
import { Link } from 'react-router-dom'
import TierBadge from '../components/TierBadge.jsx'
import '../styles/add-data.css'

const SOURCES = [
  {
    id: 'bank',
    name: 'Bank account',
    how: 'Connect with Consumer Data Right (CDR). You approve the share at your bank; no file needed.',
    tier: 'C',
    button: 'Connect bank',
    done: 'Connected (demo)',
  },
  {
    id: 'mygov',
    name: 'myGov income statement (STP)',
    how: 'Download it from myGov (ATO online services) and add it here. Tax secrecy law stops banks getting it from the ATO directly.',
    tier: 'A',
    button: 'Upload PDF',
    done: 'Added (demo)',
  },
  {
    id: 'platform',
    name: 'Platform earnings statement',
    how: 'Export it from the delivery platform.',
    tier: 'B',
    button: 'Upload file',
    done: 'Added (demo)',
  },
  {
    id: 'invoices',
    name: 'Invoices for contract work',
    how: 'Invoices you sent, matched to the deposits that paid them.',
    tier: 'C',
    button: 'Upload invoices',
    done: 'Added (demo)',
  },
  {
    id: 'manual',
    name: 'Shifts and cash income',
    how: 'Enter them yourself. Self-reported items are tier D and never appear in an income proof.',
    tier: 'D',
    button: 'Enter manually',
    done: 'Entered (demo)',
  },
]

// Demo of the step where the worker gives evidence to the issuer. Nothing is uploaded or processed.
export default function AddData() {
  const [added, setAdded] = useState({})

  return (
    <main className="add-data-page">
      <h1>Add your data</h1>
      <p className="add-data-note" role="note">
        Demo: nothing is uploaded or processed. Mei's data is already loaded.
      </p>
      <ul className="add-data-list">
        {SOURCES.map((s) => (
          <li key={s.id} className="add-data-row">
            <h2>{s.name}</h2>
            <p>{s.how}</p>
            <p>
              <TierBadge tier={s.tier} />
            </p>
            <div className="add-data-actions">
              <button type="button" onClick={() => setAdded((prev) => ({ ...prev, [s.id]: true }))}>
                {s.button}
              </button>
              <span className="add-data-status" aria-live="polite">
                {added[s.id] ? s.done : 'Not added'}
              </span>
            </div>
          </li>
        ))}
      </ul>
      <p>
        BaeSlip checks each document against your bank deposits. Self-reported items never count toward the income in a proof.
      </p>
      <p>
        <Link to="/app">See your income</Link>
      </p>
    </main>
  )
}
