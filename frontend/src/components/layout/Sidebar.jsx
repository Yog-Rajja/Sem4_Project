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
  TimerIcon,
  UsersIcon,
  WandIcon,
  XIcon,
} from '../ui/Icons'

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: HomeIcon },
  { to: '/goals', label: 'Goals', icon: TargetIcon },
  { to: '/tasks', label: 'Tasks', icon: CheckSquareIcon },
  { to: '/focus', label: 'Focus', icon: TimerIcon },
  { to: '/studio', label: 'Studio', icon: WandIcon },
  { to: '/circles', label: 'Circles', icon: UsersIcon },
  { to: '/calendar', label: 'Calendar', icon: CalendarIcon },
  { to: '/analytics', label: 'Analytics', icon: ChartIcon },
]

function NavItems({ onNavigate }) {
  return (
    <nav className="flex flex-col gap-2 px-4 mt-4">
      {NAV.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              'group flex items-center gap-3.5 px-3 py-2.5 text-[15px] transition-colors duration-200 rounded-2xl font-sans',
              isActive
                ? 'bg-surface shadow-card font-bold text-ink'
                : 'text-ink-soft hover:bg-surface/50 hover:text-ink font-semibold',
            )
          }
        >
          {({ isActive }) => (
            <>
              <motion.div
                whileHover={{ scale: 1.1, rotate: -2 }}
                className={cn('p-1.5 rounded-xl transition-colors', isActive ? 'bg-brand-100/50 text-brand-600' : 'bg-transparent text-ink-muted group-hover:text-brand-500 group-hover:bg-brand-50/50')}
              >
                <Icon size={20} />
              </motion.div>
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
    <div className="flex items-center gap-3 px-7 py-7 mb-2">
      <motion.span
        whileHover={{ rotate: 180 }}
        transition={{ type: "spring", stiffness: 200, damping: 10 }}
        className="flex items-center justify-center bg-highlight w-10 h-10 rounded-2xl text-ink shadow-pop"
      >
        <CompassIcon size={22} />
      </motion.span>
      <span className="font-heading text-[18px] text-ink font-semibold tracking-tight">
        Smart Companion
      </span>
    </div>
  )
}

export default function Sidebar({ mobileOpen, onCloseMobile }) {
  return (
    <>
      {/* Desktop rail */}
      <aside className="hidden w-64 shrink-0 border-r border-line bg-canvas lg:flex lg:flex-col">
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
