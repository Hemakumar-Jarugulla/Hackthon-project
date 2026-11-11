import axios from 'axios'

export const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'
).replace(/\/+$/, '')

export const USE_MOCK_DATA = import.meta.env.VITE_USE_MOCK_DATA !== 'false'

const AUTH_STORAGE_KEY = 'attributioniq_auth_session'

export function readAuthSession() {
  try {
    const raw = window.localStorage.getItem(AUTH_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function writeAuthSession(session) {
  try {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session))
  } catch {
    // Ignore storage quota errors
  }
}

/**
 * Shared Axios client pre-configured for the AttributionIQ Django REST API (SimpleJWT).
 */
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

let refreshPromise = null

apiClient.interceptors.request.use((config) => {
  const session = readAuthSession()
  if (session?.token && !config.headers.Authorization) {
    config.headers.Authorization = `Bearer ${session.token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error?.config
    if (
      error?.response?.status === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !String(originalRequest.url || '').includes('/auth/refresh') &&
      !String(originalRequest.url || '').includes('/auth/login')
    ) {
      const session = readAuthSession()
      if (session?.refreshToken) {
        originalRequest._retry = true
        try {
          if (!refreshPromise) {
            refreshPromise = axios
              .post(`${API_BASE_URL}/auth/refresh/`, {
                refresh: session.refreshToken,
              })
              .then((res) => {
                const payload = res.data?.data ?? res.data
                const nextAccess = payload?.access
                const nextRefresh = payload?.refresh || session.refreshToken
                if (nextAccess) {
                  writeAuthSession({
                    ...session,
                    token: nextAccess,
                    refreshToken: nextRefresh,
                  })
                }
                return nextAccess
              })
              .finally(() => {
                refreshPromise = null
              })
          }
          const newToken = await refreshPromise
          if (newToken) {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            return apiClient(originalRequest)
          }
        } catch {
          writeAuthSession({
            isAuthenticated: false,
            user: null,
            token: null,
            refreshToken: null,
          })
        }
      }
    }
    return Promise.reject(error)
  }
)

/**
 * Unwraps Django common.responses envelopes (`{ success, message, data }`) or DRF `{ results }`.
 */
export function unwrapApiData(payload) {
  if (payload && typeof payload === 'object' && 'data' in payload && 'success' in payload) {
    return payload.data
  }
  return payload
}

/**
 * Fetches all pages cleanly from a paginated DRF ModelViewSet endpoint.
 */
export async function fetchAllPaginated(url, params = {}) {
  const firstRes = await apiClient.get(url, {
    params: { page_size: 100, ...params },
  })
  const firstPayload = unwrapApiData(firstRes.data)
  if (Array.isArray(firstPayload)) {
    return firstPayload
  }
  if (!firstPayload || !Array.isArray(firstPayload.results)) {
    return []
  }
  const items = [...firstPayload.results]
  let nextUrl = firstPayload.next
  let guard = 0
  while (nextUrl && guard < 20) {
    guard += 1
    const nextRes = await apiClient.get(nextUrl)
    const nextPayload = unwrapApiData(nextRes.data)
    if (Array.isArray(nextPayload?.results)) {
      items.push(...nextPayload.results)
      nextUrl = nextPayload.next
    } else {
      break
    }
  }
  return items
}
