import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useTheme } from '../../context/ThemeContext'
import Button from '../ui/Button'
import AlertsMenu from './AlertsMenu'
import { LogoutIcon, MenuIcon, MoonIcon, PlusIcon, SearchIcon, SunIcon } from '../ui/Icons'

export default function Topbar({ onOpenMobileNav, onOpenCommandPalette }) {
  const { user, logout } = useAuth()
  const { isDark, toggle } = useTheme()
  const navigate = useNavigate()

  const initial = (user?.first_name || user?.username || '?').charAt(0).toUpperCase()
  const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-line bg-surface/85 px-4 backdrop-blur-md sm:px-6">
      <button
        type="button"
        onClick={onOpenMobileNav}
        aria-label="Open menu"
        className="-ml-1 rounded-lg p-2 text-ink-soft transition-colors hover:bg-surface-muted lg:hidden"
      >
        <MenuIcon size={18} />
      </button>

      {/* Doubles as the discoverability hint for the keyboard shortcut. */}
      <button
        type="button"
        onClick={onOpenCommandPalette}
        className="hidden items-center gap-2 rounded-lg border border-line bg-surface-muted px-2.5 py-1.5 text-[13px] text-ink-muted transition-colors hover:border-line-strong hover:text-ink-soft sm:flex"
      >
        <SearchIcon size={15} />
        <span>Search or jump to…</span>
        <kbd className="ml-6 rounded border border-line bg-surface px-1.5 py-0.5 text-[11px]">
          {isMac ? '⌘' : 'Ctrl'} K
        </kbd>
      </button>

      <div className="ml-auto flex items-center gap-1.5 sm:gap-2.5">
        <Button size="sm" onClick={() => navigate('/goals/new')}>
          <PlusIcon size={15} />
          <span className="hidden sm:inline">New goal</span>
        </Button>

        <div className="mx-1 hidden h-5 w-px bg-line sm:block" />

        <AlertsMenu />

        <button
          type="button"
          onClick={toggle}
          aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          title={isDark ? 'Light mode' : 'Dark mode'}
          className="rounded-lg p-2 text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
        >
          {isDark ? <SunIcon size={17} /> : <MoonIcon size={17} />}
        </button>

        <div className="flex items-center gap-2">
          <span
            className="grid h-7.5 w-7.5 place-items-center rounded-full bg-brand-100 text-[12.5px] font-semibold text-brand-700"
            title={user?.username}
          >
            {initial}
          </span>
          <span className="hidden max-w-32 truncate text-[13px] font-medium text-ink lg:block">
            {user?.first_name || user?.username}
          </span>
        </div>

        <button
          type="button"
          onClick={logout}
          aria-label="Sign out"
          title="Sign out"
          className="rounded-lg p-2 text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
        >
          <LogoutIcon size={17} />
        </button>
      </div>
    </header>
  )
}
