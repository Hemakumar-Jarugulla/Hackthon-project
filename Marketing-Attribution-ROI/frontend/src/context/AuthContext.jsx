import { useCallback, useState } from 'react'
import { AuthContext } from './authStore'
import {
  apiClient,
  readAuthSession,
  unwrapApiData,
  USE_MOCK_DATA,
  writeAuthSession,
} from '../services/api'
import { adaptUserAccount } from '../services/apiAdapters'

const DEFAULT_DEMO_USER = {
  id: 'USR-2026-001',
  name: 'Alex Morgan',
  email: 'alex.morgan@attributioniq.io',
  role: 'Marketing Ops Admin',
  department: 'Revenue Operations',
  timezone: 'UTC+05:30',
}

function loadInitialSession() {
  const existing = readAuthSession()
  if (existing) {
    return existing
  }
  if (!USE_MOCK_DATA) {
    return {
      isAuthenticated: false,
      user: null,
      token: null,
      refreshToken: null,
    }
  }
  return {
    isAuthenticated: true,
    user: DEFAULT_DEMO_USER,
    token: 'mock-jwt-access-token',
    refreshToken: null,
  }
}

/**
 * Dual-mode authentication context supporting both offline demo mode
 * (`VITE_USE_MOCK_DATA=true`) and live Django SimpleJWT (`VITE_USE_MOCK_DATA=false`).
 */
export function AuthProvider({ children }) {
  const [session, setSession] = useState(loadInitialSession)

  const persist = useCallback((nextSession) => {
    setSession(nextSession)
    writeAuthSession(nextSession)
  }, [])

  const login = useCallback(
    async ({ email, username, password }) => {
      if (!USE_MOCK_DATA) {
        const res = await apiClient.post('/auth/login/', {
          email,
          username,
          password,
        })
        const data = unwrapApiData(res.data)
        const adaptedUser = adaptUserAccount(data.user)
        const nextSession = {
          isAuthenticated: true,
          user: adaptedUser,
          token: data.access,
          refreshToken: data.refresh,
        }
        persist(nextSession)
        return adaptedUser
      }

      const nextSession = {
        isAuthenticated: true,
        user: {
          ...DEFAULT_DEMO_USER,
          email: email || DEFAULT_DEMO_USER.email,
          name:
            email && email !== DEFAULT_DEMO_USER.email
              ? email
                  .split('@')[0]
                  .replace(/[._-]/g, ' ')
                  .replace(/\b\w/g, (c) => c.toUpperCase())
              : DEFAULT_DEMO_USER.name,
        },
        token: 'mock-jwt-access-token',
        refreshToken: null,
      }
      persist(nextSession)
      return nextSession.user
    },
    [persist]
  )

  const register = useCallback(
    async ({ name, email, role = 'Viewer', password, department, timezone }) => {
      if (!USE_MOCK_DATA) {
        const mappedRole =
          role === 'Revenue Analyst' || role === 'Marketing Analyst'
            ? 'Marketing Analyst'
            : 'Viewer'
        const res = await apiClient.post('/auth/register/', {
          name,
          email,
          role: mappedRole,
          password,
          department: department || 'Marketing Operations',
          timezone: timezone || 'UTC',
        })
        const data = unwrapApiData(res.data)
        const adaptedUser = adaptUserAccount(data.user)
        const nextSession = {
          isAuthenticated: true,
          user: adaptedUser,
          token: data.access,
          refreshToken: data.refresh,
        }
        persist(nextSession)
        return adaptedUser
      }

      const nextSession = {
        isAuthenticated: true,
        user: {
          ...DEFAULT_DEMO_USER,
          id: `USR-2026-${String(Math.floor(100 + Math.random() * 900))}`,
          name: name || 'New Analyst',
          email,
          role,
        },
        token: 'mock-jwt-access-token',
        refreshToken: null,
      }
      persist(nextSession)
      return nextSession.user
    },
    [persist]
  )

  const updateProfile = useCallback(
    async (updates) => {
      if (!USE_MOCK_DATA) {
        const res = await apiClient.patch('/auth/profile/', updates)
        const data = unwrapApiData(res.data)
        const adaptedUser = adaptUserAccount(data.user || data)
        const nextSession = {
          ...session,
          user: adaptedUser,
        }
        persist(nextSession)
        return adaptedUser
      }

      const nextSession = {
        ...session,
        user: {
          ...session.user,
          ...updates,
        },
      }
      persist(nextSession)
      return nextSession.user
    },
    [persist, session]
  )

  const logout = useCallback(async () => {
    const refreshToken = readAuthSession()?.refreshToken || session?.refreshToken
    if (!USE_MOCK_DATA && refreshToken) {
      try {
        await apiClient.post('/auth/logout/', { refresh: refreshToken })
      } catch {
        // Proceed with local token clear even if refresh token already expired
      }
    }
    persist({
      isAuthenticated: false,
      user: null,
      token: null,
      refreshToken: null,
    })
  }, [persist, session])

  return (
    <AuthContext.Provider
      value={{
        user: session.user,
        token: session.token,
        isAuthenticated: session.isAuthenticated,
        isMockMode: USE_MOCK_DATA,
        login,
        register,
        logout,
        updateProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
