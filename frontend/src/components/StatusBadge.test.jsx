// Tests for StatusBadge (owner: web-verify, ticket F2).
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import StatusBadge from './StatusBadge.jsx'

const CASES = [
  ['valid', '✓', 'Valid'],
  ['expired', '✗', 'Expired'],
  ['revoked', '✗', 'Revoked'],
  ['not_found', '✗', 'Not found'],
]

describe('StatusBadge', () => {
  it('each status shows its own text and symbol, not colour alone', () => {
    for (const [status, symbol, text] of CASES) {
      const { container, unmount } = render(<StatusBadge status={status} />)
      const badge = screen.getByRole('status')
      expect(badge).toHaveClass('status-badge', `status-badge--${status}`)
      expect(badge).toHaveAttribute('data-status', status)
      expect(badge).toHaveTextContent(text)
      const sym = container.querySelector('.status-badge__symbol')
      expect(sym).toHaveTextContent(symbol)
      expect(sym).toHaveAttribute('aria-hidden', 'true')
      expect(container.querySelector('.status-badge__text')).toHaveTextContent(text)
      unmount()
    }
  })

  it('null status renders the loading state', () => {
    render(<StatusBadge status={null} />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveClass('status-badge--loading')
    expect(badge).toHaveTextContent('Checking')
  })

  it('signature invalid overrides valid', () => {
    const { container } = render(<StatusBadge status="valid" signatureValid={false} />)
    const badge = screen.getByRole('status')
    expect(badge).toHaveClass('status-badge--invalid')
    expect(container.querySelector('.status-badge__text').textContent).toBe('Signature invalid')
    expect(badge.textContent).not.toMatch(/\bValid\b/)
    expect(container.querySelector('.signature-warning')).toBeInTheDocument()
  })

  it('revoked with bad signature keeps Revoked and shows the warning', () => {
    const { container } = render(<StatusBadge status="revoked" signatureValid={false} />)
    expect(screen.getByRole('status')).toHaveTextContent('Revoked')
    expect(screen.getByRole('status')).toHaveClass('status-badge--revoked')
    expect(container.querySelector('.signature-warning')).toBeInTheDocument()
  })

  it('no warning when signatureValid is true or null', () => {
    for (const sig of [true, null, undefined]) {
      const { container, unmount } = render(<StatusBadge status="valid" signatureValid={sig} />)
      expect(container.querySelector('.signature-warning')).toBeNull()
      unmount()
    }
  })
})
