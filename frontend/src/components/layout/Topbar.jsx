import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import { useTheme } from '../../context/ThemeContext'
import Button from '../ui/Button'
import AlertsMenu from './AlertsMenu'
import {
  GearIcon,
  LogoutIcon,
  MenuIcon,
  MoonIcon,
  PlusIcon,
  SearchIcon,
  SunIcon,
} from '../ui/Icons'

export default function Topbar({ onOpenMobileNav, onOpenCommandPalette }) {
  const { user, logout } = useAuth()
  const { isDark, toggle } = useTheme()
  const navigate = useNavigate()

  const initial = (user?.first_name || user?.username || '?').charAt(0).toUpperCase()
  const isMac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b border-line bg-canvas/80 px-5 sm:px-8 backdrop-blur-md">
      <motion.button
        type="button"
        onClick={onOpenMobileNav}
        whileHover={{ scale: 1.1, rotate: 10 }}
        whileTap={{ scale: 0.9 }}
        className="-ml-1 p-2 text-ink-soft transition-colors hover:bg-surface hover:text-brand-500 rounded-2xl lg:hidden shadow-card"
      >
        <MenuIcon size={20} />
      </motion.button>

      {/* Doubles as the discoverability hint for the keyboard shortcut. */}
      <button
        type="button"
        onClick={onOpenCommandPalette}
        className="hidden items-center gap-2 rounded-button border border-line bg-surface-muted px-2.5 py-1.5 text-[13px] text-ink-muted transition-colors hover:border-line-strong hover:text-ink-soft sm:flex"
      >
        <SearchIcon size={15} />
        <span>Search or jump to…</span>
        <kbd className="ml-6 rounded border border-line bg-surface px-1.5 py-0.5 text-[11px] text-ink-soft">
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

        <motion.button
          type="button"
          onClick={toggle}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.9, rotate: -20 }}
          className="rounded-2xl p-2 text-ink-muted transition-colors hover:bg-surface hover:shadow-card hover:text-highlight"
        >
          {isDark ? <SunIcon size={20} /> : <MoonIcon size={20} />}
        </motion.button>

        <motion.div whileHover={{ scale: 1.05 }} className="flex items-center gap-2 cursor-pointer bg-surface px-2 py-1 rounded-2xl shadow-card ml-2">
          <span
            className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-tr from-brand-400 to-highlight text-[14px] font-bold text-white shadow-pop"
          >
            {initial}
          </span>
          <span className="hidden max-w-32 truncate text-[14px] font-bold text-ink lg:block mr-2 font-sans">
            {user?.first_name || user?.username}
          </span>
        </motion.div>

        <motion.button
          type="button"
          whileHover={{ scale: 1.1, rotate: 15 }}
          whileTap={{ scale: 0.9 }}
          onClick={() => navigate('/settings')}
          className="rounded-2xl p-2 text-ink-muted transition-colors hover:bg-surface hover:shadow-card hover:text-sky"
        >
          <GearIcon size={20} />
        </motion.button>

        <motion.button
          type="button"
          whileHover={{ scale: 1.1, rotate: 10 }}
          whileTap={{ scale: 0.9 }}
          onClick={logout}
          className="rounded-2xl p-2 text-ink-muted transition-colors hover:bg-brand-50 hover:shadow-card hover:text-brand-500"
        >
          <LogoutIcon size={20} />
        </motion.button>
      </div>
    </header>
  )
}
