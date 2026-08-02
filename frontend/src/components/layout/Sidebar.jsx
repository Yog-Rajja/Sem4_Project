import { NavLink } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import cn from '../../lib/cn'
import {
  CalendarIcon,
  ChartIcon,
  CheckSquareIcon,
  CompassIcon,
  HomeIcon,
  TargetIcon,
  XIcon,
} from '../ui/Icons'

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: HomeIcon },
  { to: '/goals', label: 'Goals', icon: TargetIcon },
  { to: '/tasks', label: 'Tasks', icon: CheckSquareIcon },
  { to: '/calendar', label: 'Calendar', icon: CalendarIcon },
  { to: '/analytics', label: 'Analytics', icon: ChartIcon },
]

function NavItems({ onNavigate }) {
  return (
    <nav className="flex flex-col gap-0.5 px-3">
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13.5px] font-medium transition-colors duration-150',
              isActive
                ? 'bg-brand-50 text-brand-700'
                : 'text-ink-soft hover:bg-surface-muted hover:text-ink',
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon size={17} className={isActive ? 'text-brand-600' : 'text-ink-muted'} />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

function Brand() {
  return (
    <div className="flex items-center gap-2.5 px-5 py-4">
      <span className="grid h-8 w-8 place-items-center rounded-lg bg-brand-600 text-white">
        <CompassIcon size={18} />
      </span>
      <span className="text-[14.5px] font-semibold tracking-[-0.01em] text-ink">
        Smart Companion
      </span>
    </div>
  )
}

export default function Sidebar({ mobileOpen, onCloseMobile }) {
  return (
    <>
      {/* Desktop rail */}
      <aside className="hidden w-60 shrink-0 border-r border-line bg-surface lg:flex lg:flex-col">
        <Brand />
        <NavItems />
      </aside>

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <motion.div
              className="absolute inset-0 bg-ink/25"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
              onClick={onCloseMobile}
            />
            <motion.aside
              className="relative flex h-full w-64 flex-col border-r border-line bg-surface"
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            >
              <div className="flex items-center justify-between pr-3">
                <Brand />
                <button
                  type="button"
                  onClick={onCloseMobile}
                  aria-label="Close menu"
                  className="rounded-lg p-1.5 text-ink-muted hover:bg-surface-muted hover:text-ink"
                >
                  <XIcon size={17} />
                </button>
              </div>
              <NavItems onNavigate={onCloseMobile} />
            </motion.aside>
          </div>
        )}
      </AnimatePresence>
    </>
  )
}
