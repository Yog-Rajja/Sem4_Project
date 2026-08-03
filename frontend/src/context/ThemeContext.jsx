import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'

const ThemeContext = createContext(null)
const STORAGE_KEY = 'sc_theme'

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used inside <ThemeProvider>')
  return ctx
}

function systemPrefersDark() {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false
}

function resolveInitial() {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  return systemPrefersDark() ? 'dark' : 'light'
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(resolveInitial)

  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-theme', theme)
    // Applied after the first paint so switching animates but loading doesn't.
    const id = requestAnimationFrame(() => root.setAttribute('data-theme-ready', ''))
    return () => cancelAnimationFrame(id)
  }, [theme])

  // Follow the OS only while the user hasn't expressed a preference.
  useEffect(() => {
    const media = window.matchMedia?.('(prefers-color-scheme: dark)')
    if (!media) return
    const onChange = (event) => {
      if (!localStorage.getItem(STORAGE_KEY)) {
        setTheme(event.matches ? 'dark' : 'light')
      }
    }
    media.addEventListener('change', onChange)
    return () => media.removeEventListener('change', onChange)
  }, [])

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next = current === 'dark' ? 'light' : 'dark'
      localStorage.setItem(STORAGE_KEY, next)
      return next
    })
  }, [])

  const value = useMemo(
    () => ({ theme, toggle, isDark: theme === 'dark' }),
    [theme, toggle],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
