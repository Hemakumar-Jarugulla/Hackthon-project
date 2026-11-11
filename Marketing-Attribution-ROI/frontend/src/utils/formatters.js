/**
 * Joins truthy class names into a single string.
 * @param {...(string|false|null|undefined)} classes
 * @returns {string}
 */
export function cn(...classes) {
  return classes.filter(Boolean).join(' ')
}

/**
 * Formats a numeric amount into a localized currency string.
 * Safely handles null/undefined/NaN values.
 * @param {number|null|undefined} value
 * @param {string} [currency='USD']
 * @param {number} [maximumFractionDigits=0]
 * @returns {string}
 */
export function formatCurrency(value, currency = 'USD', maximumFractionDigits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '—'
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    maximumFractionDigits,
  }).format(Number(value))
}

/**
 * Formats a numeric value with thousand separators.
 * @param {number|null|undefined} value
 * @param {number} [maximumFractionDigits=0]
 * @returns {string}
 */
export function formatNumber(value, maximumFractionDigits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '—'
  }
  return new Intl.NumberFormat('en-US', {
    maximumFractionDigits,
  }).format(Number(value))
}

/**
 * Formats a numeric percentage with optional sign.
 * @param {number|null|undefined} value
 * @param {number} [decimals=1]
 * @param {boolean} [showSign=false]
 * @returns {string}
 */
export function formatPercent(value, decimals = 1, showSign = false) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '—'
  }
  const num = Number(value)
  const prefix = showSign && num > 0 ? '+' : ''
  return `${prefix}${num.toFixed(decimals)}%`
}

/**
 * Formats an ISO date string into a readable date (e.g., Nov 11, 2026).
 * @param {string|null|undefined} isoDate
 * @returns {string}
 */
export function formatDate(isoDate) {
  if (!isoDate) return '—'
  const date = new Date(isoDate)
  if (Number.isNaN(date.getTime())) return String(isoDate)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(date)
}

/**
 * Formats an ISO timestamp into date + time.
 * @param {string|null|undefined} isoDateTime
 * @returns {string}
 */
export function formatDateTime(isoDateTime) {
  if (!isoDateTime) return '—'
  const date = new Date(isoDateTime)
  if (Number.isNaN(date.getTime())) return String(isoDateTime)
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

