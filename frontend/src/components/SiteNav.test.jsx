import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import attestation from '../../../fixtures/attestation.json'
import checksFixture from '../../../fixtures/checks.json'
import explain from '../../../fixtures/explain.json'
import keys from '../../../fixtures/keys.json'
import preview from '../../../fixtures/preview.json'
import timelineFixture from '../../../fixtures/timeline.json'
import verifyValid from '../../../fixtures/verify_valid.json'
import AppRoutes from '../router.jsx'
import SiteNav from './SiteNav.jsx'

vi.mock('../api.js', () => ({
  getTimeline: vi.fn(async () => timelineFixture),
  getChecks: vi.fn(async () => checksFixture),
  explainCheck: vi.fn(async () => explain),
  previewAttestation: vi.fn(async () => preview),
  createAttestation: vi.fn(async () => attestation),
  revokeAttestation: vi.fn(async () => ({ status: 'revoked' })),
  getKeys: vi.fn(async () => keys),
  keysUrl: () => 'http://api.test/keys.json',
  KEYS_URL: 'http://api.test/keys.json',
  verifyAttestation: vi.fn(async () => verifyValid),
}))

function renderNav(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <SiteNav />
    </MemoryRouter>,
  )
}

describe('SiteNav', () => {
  it('renders nothing on /v/:id', () => {
    const { container } = renderNav('/v/att_x')
    expect(container.innerHTML).toBe('')
    expect(screen.queryByRole('navigation')).toBeNull()
    expect(screen.queryByText('My income')).toBeNull()
    expect(screen.queryByText('Add your data')).toBeNull()
    expect(screen.queryByText('The standard')).toBeNull()
  })

  it('on /app shows both links and marks My income current', () => {
    renderNav('/app')
    const mine = screen.getByRole('link', { name: 'My income' })
    const standard = screen.getByRole('link', { name: 'The standard' })
    expect(mine).toHaveAttribute('href', '/app')
    expect(standard).toHaveAttribute('href', '/spec')
    expect(mine).toHaveAttribute('aria-current', 'page')
    expect(standard).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('navigation', { name: 'Main' })).toHaveClass('site-nav')
  })

  it('shows Add your data between My income and The standard', () => {
    renderNav('/app')
    const links = screen.getAllByRole('link').map((a) => a.textContent)
    expect(links).toEqual(['My income', 'Add your data', 'The standard'])
    expect(screen.getByRole('link', { name: 'Add your data' })).toHaveAttribute('href', '/data')
  })

  it('on /spec marks The standard current', () => {
    renderNav('/spec')
    expect(screen.getByRole('link', { name: 'The standard' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'My income' })).not.toHaveAttribute('aria-current')
  })

  it('is absent next to the real verify page', async () => {
    const { container } = render(
      <MemoryRouter initialEntries={['/v/att_valid']}>
        <SiteNav />
        <AppRoutes />
      </MemoryRouter>,
    )
    await waitFor(() => {
      const badge = container.querySelector('.status-badge')
      expect(badge).not.toBeNull()
      expect(badge.dataset.status).not.toBe('loading')
    })
    expect(container.querySelector('nav')).toBeNull()
    expect(screen.queryByText('My income')).toBeNull()
    expect(screen.queryByText('The standard')).toBeNull()
  })
})
