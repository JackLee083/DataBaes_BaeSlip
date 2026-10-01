import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import AppRoutes from '../router.jsx'

function renderData() {
  return render(
    <MemoryRouter initialEntries={['/data']}>
      <AppRoutes />
    </MemoryRouter>,
  )
}

const rows = [
  ['Bank account', 'C', 'Connect bank', 'Connected (demo)'],
  ['myGov income statement (STP)', 'A', 'Upload PDF', 'Added (demo)'],
  ['Platform earnings statement', 'B', 'Upload file', 'Added (demo)'],
  ['Invoices for contract work', 'C', 'Upload invoices', 'Added (demo)'],
  ['Shifts and cash income', 'D', 'Enter manually', 'Entered (demo)'],
]

describe('AddData page at /data', () => {
  it('renders the title and the demo note', () => {
    renderData()
    expect(screen.getByRole('heading', { level: 1, name: 'Add your data' })).toBeInTheDocument()
    expect(
      screen.getByText("Demo: nothing is uploaded or processed. Mei's data is already loaded."),
    ).toBeInTheDocument()
  })

  it('shows five rows with tier badges, Not added, and a back link', () => {
    const { container } = renderData()
    const items = screen.getAllByRole('listitem').filter((li) => li.classList.contains('add-data-row'))
    expect(items).toHaveLength(5)
    rows.forEach(([name, tier, button], i) => {
      const row = items[i]
      expect(within(row).getByRole('heading', { name })).toBeInTheDocument()
      expect(row.querySelector('.tier-badge')).toHaveAttribute('data-tier', tier)
      expect(within(row).getByRole('button', { name: button })).toBeInTheDocument()
      expect(within(row).getByText('Not added')).toBeInTheDocument()
    })
    expect(container.querySelector('[aria-live="polite"]')).not.toBeNull()
    expect(screen.getByText(/Self-reported items never count toward the income in a proof/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See your income' })).toHaveAttribute('href', '/app')
  })

  it('clicking a button changes only that row status', () => {
    renderData()
    const items = screen.getAllByRole('listitem').filter((li) => li.classList.contains('add-data-row'))
    for (let i = 0; i < rows.length; i++) {
      fireEvent.click(within(items[i]).getByRole('button', { name: rows[i][2] }))
      expect(within(items[i]).getByText(rows[i][3])).toBeInTheDocument()
      items.forEach((li, j) => {
        if (j > i) expect(within(li).getByText('Not added')).toBeInTheDocument()
      })
    }
    expect(screen.queryByText('Not added')).toBeNull()
  })
})
