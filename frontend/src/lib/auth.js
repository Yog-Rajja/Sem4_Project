const ACCESS_KEY = 'sc_access'
const REFRESH_KEY = 'sc_refresh'
const USER_KEY = 'sc_user'

export const getAccessToken = () => localStorage.getItem(ACCESS_KEY)
export const getRefreshToken = () => localStorage.getItem(REFRESH_KEY)

export function storeTokens({ access, refresh }) {
  if (access) localStorage.setItem(ACCESS_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
}

export function storeUser(user) {
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function getStoredUser() {
  try {
    const raw = localStorage.getItem(USER_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function clearSession() {
  localStorage.removeItem(ACCESS_KEY)
  localStorage.removeItem(REFRESH_KEY)
  localStorage.removeItem(USER_KEY)
}
