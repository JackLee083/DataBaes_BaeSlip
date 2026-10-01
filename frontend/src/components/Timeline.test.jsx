import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import timelineFixture from '../../../fixtures/timeline.json'
import Timeline from './Timeline'
import { formatDate } from '../labels'

const DEFINITIONS = {
  A: 'Third party reported to government',
  B: 'Payer confirmed',
  C: 'Matched bank deposit',
  D: 'Self-reported only',
}

function expectCompactBadge(scope, tier) {
  const badge = scope.querySelector(`[data-tier="${tier}"]`)
  expect(badge).not.toBeNull()
  expect(badge.textContent.trim().startsWith(tier)).toBe(true)
  expect(badge).toHaveAttribute('aria-label', `Tier ${tier}: ${DEFINITIONS[tier]}`)
}

const monthBlock = (container, month) =>
  container.querySelector(`.timeline-month[data-month="${month}"]`)

describe('Timeline', () => {
  it('fixture shows A/B/C sources and the $60 D record while August attested income stays $2,620', () => {
    const { container } = render(<Timeline timeline={timelineFixture} />)

    expect(container.querySelector('.income-timeline')).not.toBeNull()
    const august = monthBlock(container, '2026-08')
    expect(within(august).getByText(/August 2026/)).toBeInTheDocument()
    expect(within(august).getByText('$2,620')).toBeInTheDocument()
    const selfReported = august.querySelector('.timeline-self-reported')
    expect(selfReported).toHaveTextContent('Self-reported cash (not attested): $60')
    expect(selfReported).not.toHaveTextContent('$2,620')
    expect(container.textContent).not.toContain('$2,680')

    const sources = container.querySelector('.timeline-sources')
    expect(within(sources).getByText('Hospitality (casual)')).toBeInTheDocument()
    expect(within(sources).getByText('Food delivery platform')).toBeInTheDocument()
    expect(within(sources).getByText('Overseas design contracts')).toBeInTheDocument()
    expect(within(sources).getByText('Private tutoring (cash)')).toBeInTheDocument()
  })

  it('every source shows a tier letter as text', () => {
    const { container } = render(<Timeline timeline={timelineFixture} />)
    const items = container.querySelectorAll('.timeline-sources li')
    expect(items).toHaveLength(4)
    const tiers = timelineFixture.sources.map((s) => s.tier)
    items.forEach((item, i) => {
      expectCompactBadge(item, tiers[i])
    })
  })

  it('groups records by paid month, ordered by paid date', () => {
    const { container } = render(<Timeline timeline={timelineFixture} />)
    const months = [...container.querySelectorAll('.timeline-month')].map((m) => m.dataset.month)
    expect(months).toEqual(['2026-04', '2026-05', '2026-06', '2026-07', '2026-08', '2026-09'])

    const august = monthBlock(container, '2026-08')
    const dates = [...august.querySelectorAll('.timeline-record')].map((r) => r.dataset.paidOn)
    expect(dates).toEqual([...dates].sort())
    expect(dates[0]).toBe('2026-08-03')
    expect(dates).toContain('2026-08-15')
    expect(dates.every((d) => d.startsWith('2026-08'))).toBe(true)
    const total = container.querySelectorAll('.timeline-record').length
    expect(total).toBe(timelineFixture.records.length)
  })

  it('shows evidence labels as readable text and the source label per record', () => {
    const { container } = render(<Timeline timeline={timelineFixture} />)
    const april = monthBlock(container, '2026-04')
    const record = april.querySelector('.timeline-record[data-record-id="inc_003"]')
    expect(record).toHaveTextContent('Hospitality (casual)')
    expect(record).toHaveTextContent('Government income statement (STP)')
    expect(record).not.toHaveTextContent('Stp income statement')
    expect(record).toHaveTextContent('Bank deposit')
    expect(record).toHaveTextContent('$661')
    expectCompactBadge(record, 'A')
  })

  it('labels the D record as self-reported and shows overseas original amounts', () => {
    const { container } = render(<Timeline timeline={timelineFixture} />)
    const d = container.querySelector('.timeline-record[data-record-id="inc_036"]')
    expect(d).toHaveTextContent('Self-reported')
    expectCompactBadge(d, 'D')
    expect(d).toHaveTextContent('$60')

    const overseas = container.querySelector('.timeline-record[data-record-id="inc_004"]')
    expect(overseas).toHaveTextContent('USD')
    expect(overseas).toHaveTextContent('$224')
    expect(overseas).toHaveTextContent('$336')
  })

  it('months are collapsed by default and all 48 records stay reachable', () => {
    const { container } = render(<Timeline timeline={timelineFixture} />)
    const months = container.querySelectorAll('details.timeline-month')
    expect(months).toHaveLength(6)
    months.forEach((m) => {
      expect(m).not.toHaveAttribute('open')
      expect(m.querySelector('summary.timeline-month-summary')).not.toBeNull()
    })
    expect(container.querySelectorAll('.timeline-record')).toHaveLength(48)
  })

  it('record dates are readable', () => {
    const { container } = render(<Timeline timeline={timelineFixture} />)
    const record = container.querySelector('.timeline-record[data-record-id="inc_003"]')
    const paidOn = record.dataset.paidOn
    expect(record).toHaveTextContent(formatDate(paidOn))
    expect(record.textContent).not.toContain(paidOn)
  })

  it('shows the tier legend once under the heading', () => {
    const { container } = render(<Timeline timeline={timelineFixture} />)
    expect(screen.getAllByText('What the tier letters mean')).toHaveLength(1)
    const text = container.textContent
    for (const definition of Object.values(DEFINITIONS)) {
      expect(text.split(definition).length - 1).toBe(1)
    }
  })

  it('shows a neutral placeholder for a null timeline', () => {
    const { container } = render(<Timeline timeline={null} />)
    expect(container.querySelector('.income-timeline')).not.toBeNull()
    expect(screen.getByText(/loading income timeline/i)).toBeInTheDocument()
    expect(screen.queryByText(/error/i)).toBeNull()
  })

  it('shows an empty message when there are no sources or records', () => {
    render(<Timeline timeline={{ sources: [], records: [], months: {} }} />)
    expect(screen.getByText(/no income recorded yet/i)).toBeInTheDocument()
  })

  it('does not mutate its prop', () => {
    const copy = structuredClone(timelineFixture)
    render(<Timeline timeline={copy} />)
    expect(copy).toEqual(timelineFixture)
  })

  it('shows the monthly chart right below the heading', () => {
    const { container } = render(<Timeline timeline={timelineFixture} />)
    const section = container.querySelector('.income-timeline')
    expect(section.querySelector('.monthly-chart')).not.toBeNull()
    expect(section.querySelectorAll('[data-month-bar]')).toHaveLength(6)
    expect(section.children[0].tagName).toBe('H2')
    expect(section.children[1]).toHaveClass('monthly-chart')
  })
})
