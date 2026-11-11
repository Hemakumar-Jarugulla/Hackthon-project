import { useContext } from 'react'
import { AuthContext } from '../context/authStore'

/**
 * Returns mock authentication state & helpers (user, isAuthenticated, login, logout, register).
 */
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}

