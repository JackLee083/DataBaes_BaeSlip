import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import checksFixture from '../../../fixtures/checks.json'
import timelineFixture from '../../../fixtures/timeline.json'
import preview from '../../../fixtures/preview.json'
import App from './App.jsx'
import { explainCheck, getChecks, getTimeline, previewAttestation } from '../api.js'

vi.mock('../api.js', () => ({
  getTimeline: vi.fn(),
  getChecks: vi.fn(),
  explainCheck: vi.fn(),
  previewAttestation: vi.fn(),
}))

const shareFlowProps = vi.hoisted(() => ({ calls: [] }))
vi.mock('../components/ShareFlow.jsx', () => ({
  default: (props) => {
    shareFlowProps.calls.push(props)
    return <section data-testid="share-flow" />
  },
}))

const checks = checksFixture.checks

function deferred() {
  let resolve
  let reject
  const promise = new Promise((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('App page', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    shareFlowProps.calls.length = 0
    previewAttestation.mockResolvedValue(preview)
  })

  it('API fixture responses render timeline and four checks while ShareFlow receives only mei and rental', async () => {
    getTimeline.mockResolvedValue(timelineFixture)
    getChecks.mockResolvedValue(checksFixture)

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Income timeline' })).toBeInTheDocument()
    for (const check of checks) {
      expect(await screen.findByRole('heading', { name: check.title })).toBeInTheDocument()
    }
    expect(getTimeline).toHaveBeenCalledWith('mei')
    expect(getChecks).toHaveBeenCalledWith('mei')
    expect(screen.getByTestId('share-flow')).toBeInTheDocument()
    for (const props of shareFlowProps.calls) {
      expect(props).toEqual({ workerId: 'mei', scope: 'rental' })
    }
  })

  it('shows loading states for both panels while requests are pending', () => {
    getTimeline.mockReturnValue(deferred().promise)
    getChecks.mockReturnValue(deferred().promise)

    render(<App />)

    const statuses = screen.getAllByRole('status').map((el) => el.textContent)
    expect(statuses.some((t) => /Loading income timeline/.test(t))).toBe(true)
    expect(statuses.some((t) => /Loading checks/.test(t))).toBe(true)
    expect(screen.getByTestId('share-flow')).toBeInTheDocument()
  })

  it('a rejected getChecks shows an error with Retry while timeline and ShareFlow still render', async () => {
    getTimeline.mockResolvedValue(timelineFixture)
    getChecks.mockRejectedValueOnce(new Error('offline'))
    getChecks.mockResolvedValueOnce(checksFixture)

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Income timeline' })).toBeInTheDocument()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/checks/i)
    expect(screen.getByTestId('share-flow')).toBeInTheDocument()

    fireEvent.click(within(alert).getByRole('button', { name: /Retry/ }))

    expect(await screen.findByRole('heading', { name: checks[0].title })).toBeInTheDocument()
    expect(getChecks).toHaveBeenCalledTimes(2)
    expect(getTimeline).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('a rejected getTimeline shows an error with Retry while checks and ShareFlow still render', async () => {
    getChecks.mockResolvedValue(checksFixture)
    getTimeline.mockRejectedValueOnce(new Error('offline'))
    getTimeline.mockResolvedValueOnce(timelineFixture)

    render(<App />)

    expect(await screen.findByRole('heading', { name: checks[0].title })).toBeInTheDocument()
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/timeline/i)
    expect(screen.getByTestId('share-flow')).toBeInTheDocument()

    fireEvent.click(within(alert).getByRole('button', { name: /Retry/ }))

    expect(await screen.findByRole('heading', { name: 'Income timeline' })).toBeInTheDocument()
    expect(getTimeline).toHaveBeenCalledTimes(2)
    expect(getChecks).toHaveBeenCalledTimes(1)
  })

  it('shows an empty message when there are no checks', async () => {
    getTimeline.mockResolvedValue(timelineFixture)
    getChecks.mockResolvedValue({ checks: [] })

    render(<App />)

    expect(await screen.findByText('No checks to review')).toBeInTheDocument()
  })

  it('passes the loaded timeline language to CheckCards', async () => {
    getTimeline.mockResolvedValue({ ...timelineFixture, language: 'en' })
    getChecks.mockResolvedValue(checksFixture)
    explainCheck.mockReturnValue(new Promise(() => {}))

    render(<App />)

    await screen.findByRole('heading', { name: 'Income timeline' })
    await waitFor(() => expect(screen.getAllByRole('button', { name: 'Explain in my language' })).toHaveLength(4))
    fireEvent.click(screen.getAllByRole('button', { name: 'Explain in my language' })[0])

    expect(explainCheck).toHaveBeenCalledWith(checks[0].check_id, 'en')
  })

  it('uses English for check cards before the timeline loads', async () => {
    getTimeline.mockReturnValue(deferred().promise)
    getChecks.mockResolvedValue(checksFixture)
    explainCheck.mockReturnValue(new Promise(() => {}))

    render(<App />)

    const buttons = await screen.findAllByRole('button', { name: 'Explain in my language' })
    fireEvent.click(buttons[0])
    expect(explainCheck.mock.calls[0][1]).toBe('en')
  })

  it('ignores results that resolve after unmount', async () => {
    const t = deferred()
    const c = deferred()
    getTimeline.mockReturnValue(t.promise)
    getChecks.mockReturnValue(c.promise)
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const { unmount } = render(<App />)
    unmount()
    await act(async () => {
      t.resolve(timelineFixture)
      c.reject(new Error('late'))
      await Promise.resolve()
    })

    expect(errorSpy).not.toHaveBeenCalled()
    errorSpy.mockRestore()
  })

  it('renders sections in order: heading, description, summary, share, checks, timeline', async () => {
    getTimeline.mockResolvedValue(timelineFixture)
    getChecks.mockResolvedValue(checksFixture)

    const { container } = render(<App />)

    const timelineHeading = await screen.findByRole('heading', { name: 'Income timeline' })
    await screen.findByRole('heading', { name: checks[0].title })
    const intro = container.querySelector('.app-intro')
    expect(intro.textContent).toMatch(/^Illustrative demo/)
    const ordered = [
      screen.getByRole('heading', { level: 1, name: "Mei's income proof" }),
      intro,
      screen.getByRole('heading', { name: 'Income summary' }),
      screen.getByTestId('share-flow'),
      screen.getByRole('heading', { name: 'Checks for you only' }),
      timelineHeading,
    ]
    for (let i = 0; i < ordered.length - 1; i++) {
      expect(ordered[i].compareDocumentPosition(ordered[i + 1]) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    }
  })

  it('Create a rental proof moves focus to the share section', async () => {
    getTimeline.mockResolvedValue(timelineFixture)
    getChecks.mockResolvedValue(checksFixture)

    render(<App />)

    fireEvent.click(await screen.findByRole('button', { name: 'Create a rental proof' }))

    expect(document.activeElement).toBe(document.getElementById('share-section'))
    expect(document.activeElement).toContainElement(screen.getByTestId('share-flow'))
  })

  it('the summary loads independently: a failing preview shows its own Retry while timeline, checks and share still render', async () => {
    getTimeline.mockResolvedValue(timelineFixture)
    getChecks.mockResolvedValue(checksFixture)
    previewAttestation.mockReset()
    previewAttestation.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(preview)

    render(<App />)

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(/income summary/i)
    expect(await screen.findByRole('heading', { name: 'Income timeline' })).toBeInTheDocument()
    expect(await screen.findByRole('heading', { name: checks[0].title })).toBeInTheDocument()
    expect(screen.getByTestId('share-flow')).toBeInTheDocument()

    fireEvent.click(within(alert).getByRole('button', { name: /Retry/ }))

    expect(await screen.findByText(/\$2,700/)).toBeInTheDocument()
  })

  it('each full tier definition appears at most once on /app', async () => {
    getTimeline.mockResolvedValue(timelineFixture)
    getChecks.mockResolvedValue(checksFixture)

    render(<App />)

    expect(await screen.findByRole('heading', { name: 'Income timeline' })).toBeInTheDocument()
    for (const check of checks) {
      expect(await screen.findByRole('heading', { name: check.title })).toBeInTheDocument()
    }
    expect(await screen.findByText(/\$2,700/)).toBeInTheDocument()

    const text = document.body.textContent
    for (const definition of [
      'Third party reported to government',
      'Payer confirmed',
      'Matched bank deposit',
      'Self-reported only',
    ]) {
      expect(text.split(definition).length - 1).toBeLessThanOrEqual(1)
    }
    const compact = document.querySelectorAll('.tier-badge--compact')
    expect(compact.length).toBeGreaterThan(0)
    compact.forEach((badge) => {
      expect(badge.textContent.trim().startsWith(badge.dataset.tier)).toBe(true)
    })
  })
})
