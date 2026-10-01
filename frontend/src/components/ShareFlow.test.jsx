// Tests for ShareFlow (owner: web-verify, F5). api.js is mocked with the real fixtures.
import { render, screen, within, fireEvent, waitFor } from '@testing-library/react'
import { QRCodeSVG } from 'qrcode.react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import preview from '../../../fixtures/preview.json'
import issued from '../../../fixtures/attestation.json'
import revoked from '../../../fixtures/revoke.json'
import { createAttestation, previewAttestation, revokeAttestation } from '../api.js'
import ShareFlow from './ShareFlow.jsx'

vi.mock('../api.js', () => ({
  previewAttestation: vi.fn(),
  createAttestation: vi.fn(),
  revokeAttestation: vi.fn(),
}))

const PREVIEW_BTN = 'Preview what will be shared'
const CREATE_BTN = 'Create rental attestation'
const REVOKE_BTN = 'Revoke'

beforeEach(() => {
  vi.resetAllMocks()
  previewAttestation.mockResolvedValue(preview)
  createAttestation.mockResolvedValue(issued)
  revokeAttestation.mockResolvedValue(revoked)
})

async function doPreview() {
  fireEvent.click(screen.getByRole('button', { name: PREVIEW_BTN }))
  await screen.findByText('Will be shared')
}

async function doCreate() {
  await doPreview()
  fireEvent.click(screen.getByRole('button', { name: CREATE_BTN }))
  await screen.findByRole('link', { name: issued.verify_url })
}

function box(cls) {
  return within(document.querySelector(cls))
}

describe('ShareFlow', () => {
  it('nothing is fetched on mount', () => {
    render(<ShareFlow />)
    expect(previewAttestation).not.toHaveBeenCalled()
    expect(createAttestation).not.toHaveBeenCalled()
  })

  it('preview lists carry no lang attribute', async () => {
    render(<ShareFlow />)
    await doPreview()
    for (const cls of ['.share-preview-included', '.share-preview-excluded']) {
      expect(document.querySelector(`${cls} ul`).hasAttribute('lang')).toBe(false)
    }
  })

  it('the preview toggles: Hide preview hides it, showing again does not refetch', async () => {
    render(<ShareFlow />)
    const btn = screen.getByRole('button', { name: PREVIEW_BTN })
    expect(btn).toHaveAttribute('aria-expanded', 'false')
    await doPreview()
    const hide = screen.getByRole('button', { name: 'Hide preview' })
    expect(hide).toHaveAttribute('aria-expanded', 'true')
    const controls = hide.getAttribute('aria-controls')
    expect(document.getElementById(controls)).toContainElement(screen.getByText('Will be shared'))
    fireEvent.click(hide)
    expect(screen.queryByText('Will be shared')).toBeNull()
    expect(screen.queryByText('Will not be shared')).toBeNull()
    expect(screen.queryByRole('button', { name: CREATE_BTN })).toBeNull()
    expect(screen.getByRole('button', { name: PREVIEW_BTN })).toHaveAttribute('aria-expanded', 'false')
    fireEvent.click(screen.getByRole('button', { name: PREVIEW_BTN }))
    expect(screen.getByText('Will be shared')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: CREATE_BTN })).toBeInTheDocument()
    expect(previewAttestation).toHaveBeenCalledTimes(1)
  })

  it('an issued QR stays visible while the preview is hidden', async () => {
    render(<ShareFlow />)
    await doCreate()
    fireEvent.click(screen.getByRole('button', { name: 'Hide preview' }))
    expect(screen.queryByText('Will be shared')).toBeNull()
    expect(document.querySelector('.share-qr svg')).not.toBeNull()
  })

  it('create button appears only after preview', async () => {
    render(<ShareFlow />)
    expect(screen.queryByRole('button', { name: CREATE_BTN })).toBeNull()
    await doPreview()
    expect(screen.getByRole('button', { name: CREATE_BTN })).toBeInTheDocument()
  })

  it('preview renders every label from fixtures/preview.json', async () => {
    render(<ShareFlow />)
    await doPreview()
    expect(previewAttestation).toHaveBeenCalledWith('mei', 'rental')
    const inc = box('.share-preview-included')
    const exc = box('.share-preview-excluded')
    expect(inc.getByText('Will be shared')).toBeInTheDocument()
    expect(exc.getByText('Will not be shared')).toBeInTheDocument()
    expect(preview.included).toHaveLength(7)
    expect(preview.excluded).toHaveLength(6)
    for (const item of preview.included) expect(inc.getByText(item.label)).toBeInTheDocument()
    for (const item of preview.excluded) {
      expect(exc.getByText(item.label)).toBeInTheDocument()
      expect(inc.queryByText(item.label)).toBeNull()
    }
    expect(exc.getByText('Hours and shifts')).toBeInTheDocument()
    expect(exc.getByText('Visa status')).toBeInTheDocument()
    expect(exc.getAllByText(/never shared/)).toHaveLength(4)
    expect(exc.getAllByText(/not in rental scope/)).toHaveLength(2)
  })

  it('create renders a QR whose value is verify_url from fixtures/attestation.json', async () => {
    render(<ShareFlow />)
    await doPreview()
    fireEvent.click(screen.getByRole('button', { name: CREATE_BTN }))
    const link = await screen.findByRole('link', { name: issued.verify_url })
    expect(createAttestation).toHaveBeenCalledWith('mei', 'rental')
    expect(link.getAttribute('href')).toBe(issued.verify_url)
    expect(screen.getByText('Valid until 2026-10-29')).toBeInTheDocument()
    const svg = document.querySelector('.share-qr svg')
    const ref = render(
      <QRCodeSVG value={issued.verify_url} title="QR code for the verify link" />,
    ).container.querySelector('svg')
    expect(svg.outerHTML).toBe(ref.outerHTML)
  })

  it('a failed preview shows an alert and allows retry', async () => {
    previewAttestation.mockReset()
    previewAttestation.mockRejectedValueOnce(new Error('boom')).mockResolvedValueOnce(preview)
    render(<ShareFlow />)
    fireEvent.click(screen.getByRole('button', { name: PREVIEW_BTN }))
    expect((await screen.findByRole('alert')).textContent).toContain('boom')
    fireEvent.click(screen.getByRole('button', { name: PREVIEW_BTN }))
    await screen.findByText('Will be shared')
    expect(screen.queryByRole('alert')).toBeNull()
    expect(previewAttestation).toHaveBeenCalledTimes(2)
  })

  it('buttons are disabled while a request is in flight', async () => {
    let resolve
    previewAttestation.mockReturnValue(new Promise((r) => { resolve = r }))
    render(<ShareFlow />)
    fireEvent.click(screen.getByRole('button', { name: PREVIEW_BTN }))
    expect(screen.getByRole('button', { name: PREVIEW_BTN })).toBeDisabled()
    expect(screen.getByText('Loading…')).toBeInTheDocument()
    resolve(preview)
    await waitFor(() => expect(screen.getByRole('button', { name: 'Hide preview' })).not.toBeDisabled())
    expect(screen.queryByText('Loading…')).toBeNull()
  })

  it('revoke calls revokeAttestation with att_Qm3vX9kT2pA, hides the QR and shows revoked_at from fixtures/revoke.json', async () => {
    render(<ShareFlow />)
    await doCreate()
    fireEvent.click(screen.getByRole('button', { name: REVOKE_BTN }))
    await screen.findByText('Revoked at 2026-09-29 10:05')
    expect(revokeAttestation).toHaveBeenCalledWith(issued.attestation.attestation_id)
    expect(issued.attestation.attestation_id).toBe('att_Qm3vX9kT2pA')
    expect(document.querySelector('.share-qr')).toBeNull()
    expect(document.querySelector('svg')).toBeNull()
    const note = box('.share-revoked')
    expect(note.getByText(issued.verify_url)).toBeInTheDocument()
    expect(note.getByText(/Anyone who opens the link now sees/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: CREATE_BTN })).not.toBeDisabled()
  })

  it('a failed revoke shows an alert and keeps the QR for retry', async () => {
    revokeAttestation.mockReset()
    revokeAttestation.mockRejectedValueOnce(new Error('nope')).mockResolvedValueOnce(revoked)
    render(<ShareFlow />)
    await doCreate()
    fireEvent.click(screen.getByRole('button', { name: REVOKE_BTN }))
    expect((await screen.findByRole('alert')).textContent).toContain('nope')
    expect(document.querySelector('.share-qr svg')).not.toBeNull()
    expect(document.querySelector('.share-revoked')).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: REVOKE_BTN }))
    await screen.findByText('Revoked at 2026-09-29 10:05')
    expect(screen.queryByRole('alert')).toBeNull()
    expect(revokeAttestation).toHaveBeenCalledTimes(2)
  })

  it('revoke button is disabled while revoking', async () => {
    let resolve
    revokeAttestation.mockReturnValue(new Promise((r) => { resolve = r }))
    render(<ShareFlow />)
    await doCreate()
    fireEvent.click(screen.getByRole('button', { name: REVOKE_BTN }))
    expect(screen.getByRole('button', { name: REVOKE_BTN })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Hide preview' })).toBeDisabled()
    expect(screen.getByRole('button', { name: CREATE_BTN })).toBeDisabled()
    resolve(revoked)
    await screen.findByText('Revoked at 2026-09-29 10:05')
    expect(screen.getByRole('button', { name: 'Hide preview' })).not.toBeDisabled()
  })

  it('creating again after revoke shows a new QR and clears the revoked notice', async () => {
    render(<ShareFlow />)
    await doCreate()
    fireEvent.click(screen.getByRole('button', { name: REVOKE_BTN }))
    await screen.findByText('Revoked at 2026-09-29 10:05')
    fireEvent.click(screen.getByRole('button', { name: CREATE_BTN }))
    await waitFor(() => expect(document.querySelector('.share-qr svg')).not.toBeNull())
    expect(document.querySelector('.share-revoked')).toBeNull()
    expect(screen.queryByText(/Revoked at/)).toBeNull()
    expect(createAttestation).toHaveBeenCalledTimes(2)
  })
})
