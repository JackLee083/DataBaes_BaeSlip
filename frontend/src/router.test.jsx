import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import AppRoutes from './router.jsx'

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

describe('routes', () => {
  it('/app renders Mei\'s app with the share flow', () => {
    renderAt('/app')
    expect(screen.getByRole('heading', { level: 1, name: /Mei's income/ })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /Share a rental attestation/ })).toBeInTheDocument()
  })

  it('/v/:id renders the verify page with the id', () => {
    renderAt('/v/att_7f3c2a')
    expect(screen.getByRole('heading', { level: 1, name: /Verify/ })).toBeInTheDocument()
    expect(screen.getByText(/att_7f3c2a/)).toBeInTheDocument()
  })

  it('/spec renders the spec page', () => {
    renderAt('/spec')
    expect(screen.getByRole('heading', { level: 1, name: /BaeSlip standard/ })).toBeInTheDocument()
  })

  it('unknown paths redirect to /app', () => {
    renderAt('/nope')
    expect(screen.getByRole('heading', { level: 1, name: /Mei's income/ })).toBeInTheDocument()
  })
})
