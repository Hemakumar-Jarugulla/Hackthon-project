import { createContext } from 'react'

export const AppContext = createContext(null)

export const DATE_RANGE_OPTIONS = [
  { value: 'last_30_days', label: 'Last 30 Days' },
  { value: 'last_90_days', label: 'Last 90 Days' },
  { value: 'ytd_2026', label: 'Year to Date (2026)' },
  { value: 'all_time', label: 'Full Dataset (2026)' },
]
