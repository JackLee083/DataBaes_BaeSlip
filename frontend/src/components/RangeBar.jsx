import '../styles/charts.css'

// Horizontal bar for the supplied monthly income range with a median marker.
// Labels are the caller's pre-formatted strings; the numbers are only used to
// place the marker. Nothing is computed for display.
const PAD = 4
const SPAN = 100 - PAD * 2

export default function RangeBar({ low, high, median, lowLabel, highLabel, medianLabel, showMedianValue = true }) {
  const fraction = high > low ? Math.min(1, Math.max(0, (median - low) / (high - low))) : 0.5
  const x = PAD + SPAN * fraction
  return (
    <div className="range-bar">
      <svg
        viewBox="0 0 100 20"
        preserveAspectRatio="none"
        role="img"
        aria-label={`Monthly income range ${lowLabel} to ${highLabel}, median ${medianLabel}`}
      >
        <rect className="range-bar__track" x="0" y="6" width="100" height="8" rx="2" />
        <rect className="range-bar__band" x={PAD} y="3" width={SPAN} height="14" rx="2" />
        <line data-testid="range-median" className="range-bar__median" x1={x} x2={x} y1="0" y2="20" />
      </svg>
      <p className="range-bar__labels">
        <span>{`Low ${lowLabel}`}</span>
        <span>{showMedianValue ? `Median ${medianLabel}` : 'Median'}</span>
        <span>{`High ${highLabel}`}</span>
      </p>
    </div>
  )
}
