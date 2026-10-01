import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import checksFixture from '../../../fixtures/checks.json'
import explainFixture from '../../../fixtures/explain.json'
import CheckCard from './CheckCard'
import { explainCheck } from '../api.js'

vi.mock('../api.js', () => ({ explainCheck: vi.fn() }))

const checks = checksFixture.checks
const checkFor = (rule) => checks.find((check) => check.rule === rule)

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('CheckCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(cleanup)

  it('summarizes each rule from supplied values and keeps one Details section closed initially', () => {
    const suppliedChecks = [
      { ...checkFor('R1'), difference_cents: 12345 },
      { ...checkFor('R2'), difference_cents: 6789 },
      { ...checkFor('R3'), facts: { ...checkFor('R3').facts, business_days_late: 2 } },
      { ...checkFor('R4'), facts: { ...checkFor('R4').facts, total_hours: 53, limit_hours: 47 } },
    ]
    const expectations = [
      ['Minimum hourly rate', 'Needs review', 'Difference $123.45'],
      ['Delivery minimum', 'Needs review', 'Difference $67.89'],
      ['Super payment timing', 'Needs review', '2 business days late'],
      ['Student visa hours', 'Heads-up', '53 of 47 hours'],
    ]

    const { container } = render(<>{suppliedChecks.map((check) => <CheckCard key={check.rule} check={check} />)}</>)

    const cards = container.querySelectorAll('.check-card')
    for (const [index, [rule, severity, figure]] of expectations.entries()) {
      const summary = within(cards[index].querySelector('.check-card__summary'))
      expect(summary.getByText(rule)).toBeInTheDocument()
      expect(summary.getByText(severity)).toBeInTheDocument()
      expect(summary.getByText(figure)).toBeInTheDocument()
    }
    expect(screen.getByText('1–14 Sep 2026')).toBeInTheDocument()
    expect(screen.getByText('16–25 Sep 2026')).toBeInTheDocument()
    expect(screen.getByText('28 Sep – 11 Oct 2026')).toBeInTheDocument()
    expect(container.querySelectorAll('details')).toHaveLength(4)
    for (const details of container.querySelectorAll('details')) {
      expect(details).not.toHaveAttribute('open')
      expect(details.querySelector('summary')).toHaveTextContent('Details')
    }
  })

  it.each([
    ['info', 'For your information', 'ℹ'],
    ['review', 'Needs review', '⚠'],
    ['warning', 'Heads-up', '▲'],
  ])('severity remains identifiable without colour: %s', (severity, label, icon) => {
    const check = { ...checkFor('R1'), severity }
    const { container } = render(<CheckCard check={check} />)

    const card = container.querySelector(`.check-card--${severity}`)
    expect(card).toBeInTheDocument()
    const severityIndicator = within(card).getByText(label)
    expect(severityIndicator).toBeInTheDocument()
    const severityIcon = card.querySelector('.check-card__severity-icon')
    expect(severityIcon).toHaveTextContent(icon)
    expect(severityIcon).toHaveAttribute('aria-hidden', 'true')
  })

  it('R1 renders supplied $661, $440 and $221 and requests English for its check id', async () => {
    const response = deferred()
    explainCheck.mockReturnValueOnce(response.promise)
    const r1 = checkFor('R1')

    render(<CheckCard check={r1} />)

    expect(screen.getByText('Pay may be below the minimum rate')).toBeInTheDocument()
    expect(screen.getByText('Needs review')).toBeInTheDocument()
    expect(screen.getByText('1–14 Sep 2026')).toBeInTheDocument()
    expect(screen.getByText('Difference $221.00')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Details'))
    expect(screen.getByText('Expected')).toBeInTheDocument()
    expect(screen.getByText('$661.00')).toBeInTheDocument()
    expect(screen.getByText('Actual')).toBeInTheDocument()
    expect(screen.getAllByText('$440.00')).not.toHaveLength(0)
    expect(screen.getByText('Possible explanations')).toBeInTheDocument()
    expect(screen.getByText('Next steps')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Explain in my language' }))

    expect(explainCheck).toHaveBeenCalledWith('r1-abc-cafe-2026-09-01', 'en')
    expect(screen.getByRole('button')).toBeDisabled()
    expect(screen.getByRole('status')).toHaveTextContent('Loading explanation…')
    response.resolve(explainFixture)
    await screen.findByText('AI explanation')
    const explanation = document.querySelector('.check-explanation p')
    expect(explanation?.textContent).toBe(explainFixture.text)
    expect(explanation).toHaveAttribute('lang', 'en')
  })

  it('treats a template response as a successful standard explanation', async () => {
    explainCheck.mockResolvedValueOnce({ text: 'A standard explanation', source: 'template' })

    render(<CheckCard check={checkFor('R1')} />)
    fireEvent.click(screen.getByRole('button', { name: /Explain in my language/ }))

    await waitFor(() => expect(screen.getByRole('heading', { name: 'Standard explanation' })).toBeInTheDocument())
    expect(screen.getByText('A standard explanation')).toHaveAttribute('lang', 'en')
    expect(screen.queryByText('Unable to load an explanation.')).not.toBeInTheDocument()
  })

  it('keeps facts visible after an explanation failure and lets the worker retry', async () => {
    explainCheck.mockRejectedValueOnce(new Error('offline'))
    explainCheck.mockResolvedValueOnce({ text: 'The explanation after a retry', source: 'ai' })

    render(<CheckCard check={checkFor('R1')} />)
    fireEvent.click(screen.getByRole('button', { name: /Explain in my language/ }))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Unable to load an explanation.'))
    expect(screen.getByText('Difference $221.00')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Retry explanation' }))

    await screen.findByText('The explanation after a retry')
    expect(explainCheck).toHaveBeenCalledTimes(2)
  })

  it('renders R2 supplied monetary values, calculation inputs, and limitations', () => {
    render(<CheckCard check={checkFor('R2')} />)

    expect(screen.getByText('Difference $31.70')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Details'))
    expect(screen.getByText('Engaged minutes')).toBeInTheDocument()
    expect(screen.getByText('540')).toBeInTheDocument()
    expect(screen.getByText('Limitations')).toBeInTheDocument()
    expect(screen.getByText('Platform exports may not include engaged time.')).toBeInTheDocument()
  })

  it('renders R3 timing facts without fabricating a money comparison', () => {
    render(<CheckCard check={checkFor('R3')} />)

    expect(screen.getByText('Super timing needs review')).toBeInTheDocument()
    expect(screen.getByText('1 business day late')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Details'))
    expect(screen.getByText('Deadline')).toBeInTheDocument()
    expect(screen.getByText('25 Sep 2026')).toBeInTheDocument()
    expect(screen.getByText('Received on')).toBeInTheDocument()
    expect(screen.getByText('28 Sep 2026')).toBeInTheDocument()
    expect(screen.getByText('Business days late')).toBeInTheDocument()
    expect(screen.getByText('1')).toBeInTheDocument()
    expect(screen.queryByText('Expected')).not.toBeInTheDocument()
    expect(screen.queryByText('Actual')).not.toBeInTheDocument()
    expect(screen.queryByText('Difference')).not.toBeInTheDocument()
    expect(screen.queryByText('$52.80')).not.toBeInTheDocument()
  })

  it('renders R4 supplied total, limit, and planned shifts without recalculating them', () => {
    render(<CheckCard check={checkFor('R4')} />)

    expect(screen.getByText('50 of 48 hours')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Details'))
    expect(screen.getByText('Total hours')).toBeInTheDocument()
    expect(screen.getByText('50')).toBeInTheDocument()
    expect(screen.getByText('Limit hours')).toBeInTheDocument()
    expect(screen.getByText('48')).toBeInTheDocument()
    expect(screen.getByText('Planned shifts')).toBeInTheDocument()
    expect(screen.getByText('30 Sep 2026: 8 hours')).toBeInTheDocument()
    expect(screen.getByText('11 Oct 2026: 4 hours')).toBeInTheDocument()
  })

  it('formats facts without duplicate source rows or raw evidence/date codes', () => {
    const sourceFallback = {
      ...checkFor('R1'),
      facts: {
        ...checkFor('R1').facts,
        source_label: undefined,
        counts_platform_online_time: false,
      },
    }

    const { container } = render(
      <>
        {[checkFor('R1'), checkFor('R3'), checkFor('R4'), sourceFallback].map((check, index) => (
          <CheckCard key={`${check.check_id}-${index}`} check={check} />
        ))}
      </>,
    )

    for (const details of container.querySelectorAll('details')) fireEvent.click(within(details).getByText('Details'))

    expect(screen.getAllByText('Hospitality (casual)')).toHaveLength(2)
    expect(screen.getAllByText('abc-cafe')).toHaveLength(1)
    expect(screen.getAllByText('Government income statement (STP)')).toHaveLength(2)
    expect(screen.getByText('Yes')).toBeInTheDocument()
    expect(screen.getByText('No')).toBeInTheDocument()

    for (const date of ['16 Sep 2026', '25 Sep 2026', '28 Sep 2026']) {
      expect(screen.getAllByText(date).length).toBeGreaterThan(0)
    }
    for (const shift of [
      '30 Sep 2026: 8 hours', '1 Oct 2026: 8 hours', '3 Oct 2026: 6 hours',
      '4 Oct 2026: 4 hours', '5 Oct 2026: 4 hours', '7 Oct 2026: 6 hours',
      '9 Oct 2026: 4 hours', '10 Oct 2026: 6 hours', '11 Oct 2026: 4 hours',
    ]) {
      expect(screen.getByText(shift)).toBeInTheDocument()
    }

    for (const rawValue of ['stp_income_statement', '2026-09-16', '2026-09-25', '2026-09-28', '2026-09-30', '2026-10-01', '2026-10-11']) {
      expect(screen.queryByText(rawValue)).not.toBeInTheDocument()
    }
  })

  // The live backend sends facts that fixtures/checks.json does not have (found 2026-09-30).
  // These shapes are copied from GET /workers/mei/checks on the running backend.
  const liveR1 = () => ({
    ...checkFor('R1'),
    facts: {
      ...checkFor('R1').facts,
      period_start: '2026-09-01',
      period_end: '2026-09-14',
      verification_status: 'stp_income_statement',
      award_limitation: 'This configured casual minimum may not apply where an award or agreement applies.',
    },
  })
  const liveR3 = () => ({ ...checkFor('R3'), facts: { ...checkFor('R3').facts, as_of: '2026-09-29', status: 'received_late' } })
  const detailsText = (container) => {
    fireEvent.click(within(container).getByText('Details'))
    return container.querySelector('.check-card__details').textContent
  }

  it('formats the extra R1 facts the live backend sends, with no raw codes or ISO dates', () => {
    const { container } = render(<CheckCard check={liveR1()} />)
    const text = detailsText(container)

    expect(text).not.toMatch(/\d{4}-\d{2}-\d{2}/)
    expect(text).not.toMatch(/[a-z]+_[a-z]+/)
    expect(text).toContain('Period start1 Sep 2026')
    expect(text).toContain('Period end14 Sep 2026')
    expect(text).toContain('Verified byGovernment income statement (STP)')
    expect(text).toContain('Award note')
  })

  it('formats the extra R3 facts the live backend sends, with no raw codes or ISO dates', () => {
    const { container } = render(<CheckCard check={liveR3()} />)
    const text = detailsText(container)

    expect(text).not.toMatch(/\d{4}-\d{2}-\d{2}/)
    expect(text).not.toMatch(/[a-z]+_[a-z]+/)
    expect(text).toContain('As of29 Sep 2026')
    expect(text).toContain('StatusReceived late')
  })

  it('renders explanation responses as plain text instead of HTML', async () => {
    explainCheck.mockResolvedValueOnce({ text: '<strong>Plain text</strong>', source: 'ai' })

    render(<CheckCard check={checkFor('R1')} />)
    fireEvent.click(screen.getByRole('button', { name: /Explain in my language/ }))

    expect(await screen.findByText('<strong>Plain text</strong>')).toBeInTheDocument()
    expect(document.querySelector('.check-explanation strong')).toBeNull()
  })

  it('renders no card until a check is supplied', () => {
    const { container } = render(<CheckCard check={null} />)

    expect(container).toBeEmptyDOMElement()
  })

  it('forwards another requested language without adding a translated hint', async () => {
    explainCheck.mockResolvedValueOnce({ text: 'A supplied explanation', source: 'ai' })

    const { container } = render(<CheckCard check={checkFor('R1')} language="zh-Hant" />)

    const details = container.querySelector('details')
    const button = screen.getByRole('button', { name: 'Explain in my language' })
    expect(details).not.toHaveAttribute('open')
    expect(details).not.toContainElement(button)
    expect(button).toHaveTextContent(/^Explain in my language$/)

    fireEvent.click(button)

    expect(explainCheck).toHaveBeenCalledWith('r1-abc-cafe-2026-09-01', 'zh-Hant')
    expect(details).not.toHaveAttribute('open')
    expect(await screen.findByText('A supplied explanation')).toHaveAttribute('lang', 'zh-Hant')
  })

  it('toggles a loaded explanation without calling explainCheck again', async () => {
    explainCheck.mockResolvedValueOnce({ text: 'Cached explanation', source: 'ai' })

    render(<CheckCard check={checkFor('R1')} />)
    const button = screen.getByRole('button', { name: 'Explain in my language' })
    expect(button).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(button)
    expect(await screen.findByText('Cached explanation')).toBeVisible()

    const hide = screen.getByRole('button', { name: 'Hide explanation' })
    expect(hide).toHaveAttribute('aria-expanded', 'true')
    const controlled = document.getElementById(hide.getAttribute('aria-controls'))
    expect(controlled).toContainElement(screen.getByText('Cached explanation'))

    fireEvent.click(hide)
    expect(screen.getByText('Cached explanation')).not.toBeVisible()
    const show = screen.getByRole('button', { name: 'Explain in my language' })
    expect(show).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(show)
    expect(screen.getByText('Cached explanation')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Hide explanation' })).toHaveAttribute('aria-expanded', 'true')
    expect(explainCheck).toHaveBeenCalledTimes(1)
  })

  it('renders a visual for each rule inside the summary header', () => {
    const { container } = render(<>{checks.map((check) => <CheckCard key={check.check_id} check={check} />)}</>)

    for (const card of container.querySelectorAll('.check-card')) {
      expect(card.querySelector('.check-card__summary [role="img"]')).toBeInTheDocument()
    }
  })
})
