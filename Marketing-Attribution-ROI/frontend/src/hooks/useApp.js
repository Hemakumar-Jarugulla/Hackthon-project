import { useContext } from 'react'
import { AppContext } from '../context/appStore'

/**
 * Returns global application state (dateRange, globalSearch, sidebar, notifications).
 */
export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) {
    throw new Error('useApp must be used within an AppProvider')
  }
  return ctx
}

