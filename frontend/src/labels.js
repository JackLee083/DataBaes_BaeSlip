export function evidenceLabel(kind) {
  return {
    stp_income_statement: 'Government income statement (STP)',
    notice_of_assessment: 'Tax notice of assessment',
    platform_statement: 'Platform earnings statement',
    payer_confirmed_invoice: 'Invoice confirmed by payer',
    invoice: 'Invoice',
    bank_deposit: 'Bank deposit',
    self_reported: 'Self-reported',
  }[kind] ?? kind.replaceAll('_', ' ')
}

export function ruleLabel(rule) {
  return {
    R1: 'Minimum hourly rate',
    R2: 'Delivery minimum',
    R3: 'Super payment timing',
    R4: 'Student visa hours',
  }[rule] ?? rule
}

export function severityLabel(severity) {
  return {
    info: 'For your information',
    review: 'Needs review',
    warning: 'Heads-up',
  }[severity] ?? severity
}

export function tierShortLabel(tier) {
  return {
    A: 'Gov-reported',
    B: 'Payer-confirmed',
    C: 'Bank-matched',
    D: 'Self-reported',
  }[tier] ?? tier
}

export function formatDate(iso) {
  const { day, month, year } = dateParts(iso)
  return `${day} ${monthName(month)} ${year}`
}

export function formatDateRange(start, end) {
  const first = dateParts(start)
  const last = dateParts(end)

  if (first.year === last.year && first.month === last.month && first.day === last.day) {
    return formatDate(start)
  }

  if (first.year === last.year && first.month === last.month) {
    return `${first.day}–${last.day} ${monthName(last.month)} ${last.year}`
  }

  if (first.year === last.year) {
    return `${first.day} ${monthName(first.month)} – ${last.day} ${monthName(last.month)} ${last.year}`
  }

  return `${formatDate(start)} – ${formatDate(end)}`
}

function dateParts(iso) {
  const [year, month, day] = iso.slice(0, 10).split('-')
  return { year, month: Number(month), day: Number(day) }
}

function monthName(month) {
  return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][month - 1]
}
