import audiencesSeed from '../data/audiences.json'
import attributionSeed from '../data/attribution.json'
import campaignsSeed from '../data/campaigns.json'
import channelsSeed from '../data/channels.json'
import contactsSeed from '../data/contacts.json'
import costsSeed from '../data/costs.json'
import creativesSeed from '../data/creatives.json'
import exceptionsSeed from '../data/exceptions.json'
import leadsSeed from '../data/leads.json'
import opportunitiesSeed from '../data/opportunities.json'
import ordersSeed from '../data/orders.json'
import sessionsSeed from '../data/sessions.json'
import touchpointsSeed from '../data/touchpoints.json'
import usersSeed from '../data/users.json'
import validationSeed from '../data/validation.json'

const STORAGE_PREFIX = 'attributioniq_db_v1_'

const DEFAULT_SETTINGS = {
  workspaceName: 'AttributionIQ Enterprise RevOps',
  defaultCurrency: 'USD',
  defaultAttributionModel: 'position_based',
  defaultConversionWindowDays: 90,
  defaultReportingPeriod: 'ytd_2026',
  excludePostConversionTouches: true,
  excludeDuplicateOrders: true,
  notifications: {
    criticalExceptions: true,
    missingCosts: true,
    currencyMismatch: true,
    weeklyDigest: false,
  },
}

const SEEDS = {
  campaigns: campaignsSeed,
  channels: channelsSeed,
  creatives: creativesSeed,
  audiences: audiencesSeed,
  contacts: contactsSeed,
  touchpoints: touchpointsSeed,
  sessions: sessionsSeed,
  leads: leadsSeed,
  opportunities: opportunitiesSeed,
  orders: ordersSeed,
  costs: costsSeed,
  attribution: attributionSeed,
  exceptions: exceptionsSeed,
  validation: validationSeed,
  users: usersSeed,
  settings: DEFAULT_SETTINGS,
}

function clone(value) {
  return JSON.parse(JSON.stringify(value))
}

/**
 * Reads a persisted mock entity collection from localStorage or falls back to JSON seed.
 */
export function getCollection(key) {
  try {
    const raw = window.localStorage.getItem(`${STORAGE_PREFIX}${key}`)
    if (raw) {
      return JSON.parse(raw)
    }
  } catch {
    // Fall back to deterministic seed
  }
  return clone(SEEDS[key])
}

/**
 * Persists a mock entity collection in localStorage.
 */
export function saveCollection(key, value) {
  try {
    window.localStorage.setItem(`${STORAGE_PREFIX}${key}`, JSON.stringify(value))
  } catch {
    // Ignore quota errors
  }
  return clone(value)
}

/**
 * Generates the next sequential ID matching platform conventions (e.g., CMP-2026-000009).
 */
export function generateEntityId(prefix, items) {
  const maxNum = items.reduce((max, item) => {
    const match = String(item.id || '').match(/(\d+)$/)
    const num = match ? Number(match[1]) : 0
    return Math.max(max, num)
  }, 0)
  return `${prefix}-2026-${String(maxNum + 1).padStart(6, '0')}`
}

/**
 * Clears all localStorage demo overrides back to clean seed state.
 */
export function resetAllMockData() {
  Object.keys(SEEDS).forEach((key) => {
    try {
      window.localStorage.removeItem(`${STORAGE_PREFIX}${key}`)
    } catch {
      // Ignore errors
    }
  })
}

