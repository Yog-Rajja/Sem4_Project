import axios from 'axios'
import {
  clearSession,
  getAccessToken,
  getRefreshToken,
  storeTokens,
} from './auth'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8010/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Refresh is attempted once per failed request. Concurrent 401s share a single
// in-flight refresh so we never fire several refresh calls at once.
let refreshPromise = null

function refreshAccessToken() {
  if (!refreshPromise) {
    const refresh = getRefreshToken()
    if (!refresh) return Promise.reject(new Error('no refresh token'))

    refreshPromise = axios
      .post(`${api.defaults.baseURL}/auth/refresh/`, { refresh })
      .then(({ data }) => {
        storeTokens({ access: data.access, refresh: data.refresh })
        return data.access
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    const isAuthCall = config?.url?.includes('/auth/')

    if (response?.status === 401 && !config._retried && !isAuthCall) {
      config._retried = true
      try {
        const access = await refreshAccessToken()
        config.headers.Authorization = `Bearer ${access}`
        return api(config)
      } catch {
        clearSession()
        if (!window.location.pathname.startsWith('/login')) {
          window.location.href = '/login'
        }
      }
    }
    return Promise.reject(error)
  },
)

/** Pull a human-readable message out of a DRF error response. */
export function errorMessage(error, fallback = 'Something went wrong.') {
  const data = error?.response?.data
  if (!data) return error?.message || fallback
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  const firstKey = Object.keys(data)[0]
  if (!firstKey) return fallback
  const value = data[firstKey]
  const text = Array.isArray(value) ? value[0] : value
  return typeof text === 'string' ? text : fallback
}

export default api
