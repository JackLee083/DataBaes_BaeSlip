import { useCallback, useEffect, useRef, useState } from 'react'
import Timeline from '../components/Timeline.jsx'
import CheckCard from '../components/CheckCard.jsx'
import ShareFlow from '../components/ShareFlow.jsx'
import IncomeSummary from '../components/IncomeSummary.jsx'
import { getChecks, getTimeline } from '../api.js'

// Mei's app for /app (tickets F3, F4). The timeline and checks load
// independently so one failing never blocks the other.
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

const loadTimeline = () => getTimeline('mei')
const loadChecks = () => getChecks('mei')

function PanelError({ message, onRetry }) {
  return (
    <div role="alert">
      <p>{message}</p>
      <button type="button" onClick={onRetry}>
        Retry
      </button>
    </div>
  )
}

export default function App() {
  const [timeline, retryTimeline] = useLoad(loadTimeline)
  const [checks, retryChecks] = useLoad(loadChecks)
  const language = timeline.status === 'ready' && timeline.data?.language ? timeline.data.language : 'en'
  const checkList = checks.data?.checks ?? []
  const shareRef = useRef(null)

  const focusShare = useCallback(() => {
    shareRef.current?.focus()
    shareRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
  }, [])

  return (
    <main className="app-page">
      <h1>Mei's income proof</h1>
      <p className="app-intro">
        Illustrative demo: Mei, a student-visa holder with four income sources, April to September 2026.
      </p>

      <div className="app-layout">
        <div className="app-primary">
          <IncomeSummary onCreateProof={focusShare} />
          <div id="share-section" className="app-share" tabIndex={-1} aria-label="Share your proof" ref={shareRef}>
            <ShareFlow workerId="mei" scope="rental" />
          </div>
        </div>

        <div className="app-checks">
          <section aria-labelledby="checks-heading">
            <h2 id="checks-heading">Checks for you only</h2>
            <p className="private-checks-notice">
              These checks are private to you. They are not shared with landlords or lenders, and they never appear on an
              income proof or its verify page.
            </p>
            {checks.status === 'loading' && <p role="status">Loading checks...</p>}
            {checks.status === 'error' && <PanelError message="Unable to load your checks." onRetry={retryChecks} />}
            {checks.status === 'ready' && checkList.length === 0 && <p>No checks to review</p>}
            {checks.status === 'ready' &&
              checkList.map((check) => <CheckCard key={check.check_id} check={check} language={language} />)}
          </section>
        </div>

        <div className="app-timeline">
          <section aria-label="Income timeline">
            {timeline.status === 'loading' && <p role="status">Loading income timeline...</p>}
            {timeline.status === 'error' && (
              <PanelError message="Unable to load the income timeline." onRetry={retryTimeline} />
            )}
            {timeline.status === 'ready' && !timeline.data && <p>No income timeline yet</p>}
            {timeline.status === 'ready' && timeline.data && <Timeline timeline={timeline.data} />}
          </section>
        </div>
      </div>
    </main>
  )
}
