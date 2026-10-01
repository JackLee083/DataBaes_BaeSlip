import { describe, expect, it } from 'vitest'
import {
  evidenceLabel,
  formatDate,
  formatDateRange,
  ruleLabel,
  severityLabel,
  tierShortLabel,
} from './labels.js'

describe('presentation labels', () => {
  it.each([
    ['stp_income_statement', 'Government income statement (STP)'],
    ['notice_of_assessment', 'Tax notice of assessment'],
    ['platform_statement', 'Platform earnings statement'],
    ['payer_confirmed_invoice', 'Invoice confirmed by payer'],
    ['invoice', 'Invoice'],
    ['bank_deposit', 'Bank deposit'],
    ['self_reported', 'Self-reported'],
    ['new_evidence_kind', 'new evidence kind'],
  ])('labels evidence %s', (kind, label) => {
    expect(evidenceLabel(kind)).toBe(label)
  })

  it.each([
    ['R1', 'Minimum hourly rate'],
    ['R2', 'Delivery minimum'],
    ['R3', 'Super payment timing'],
    ['R4', 'Student visa hours'],
    ['R5', 'R5'],
  ])('labels rule %s', (rule, label) => {
    expect(ruleLabel(rule)).toBe(label)
  })

  it.each([
    ['info', 'For your information'],
    ['review', 'Needs review'],
    ['warning', 'Heads-up'],
    ['other', 'other'],
  ])('labels severity %s', (severity, label) => {
    expect(severityLabel(severity)).toBe(label)
  })

  it.each([
    ['A', 'Gov-reported'],
    ['B', 'Payer-confirmed'],
    ['C', 'Bank-matched'],
    ['D', 'Self-reported'],
    ['E', 'E'],
  ])('labels tier %s', (tier, label) => {
    expect(tierShortLabel(tier)).toBe(label)
  })
})

describe('English date formatting', () => {
  it.each([
    ['2026-09-01', '1 Sep 2026'],
    ['2024-02-29', '29 Feb 2024'],
    ['2026-09-01T00:30:00+10:00', '1 Sep 2026'],
    ['2026-09-01T23:30:00-10:00', '1 Sep 2026'],
  ])('formats the supplied ISO date %s', (iso, label) => {
    expect(formatDate(iso)).toBe(label)
  })

  it.each([
    ['2026-09-01', '2026-09-14', '1–14 Sep 2026'],
    ['2026-09-28', '2026-10-11', '28 Sep – 11 Oct 2026'],
    ['2026-12-28', '2027-01-11', '28 Dec 2026 – 11 Jan 2027'],
    ['2024-02-29', '2024-02-29', '29 Feb 2024'],
    ['2026-09-01T00:30:00+10:00', '2026-09-01T23:30:00-10:00', '1 Sep 2026'],
  ])('formats range %s through %s', (start, end, label) => {
    expect(formatDateRange(start, end)).toBe(label)
  })
})
