import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import Button from '../ui/Button'
import { LogoutIcon, MenuIcon, PlusIcon } from '../ui/Icons'

export default function Topbar({ onOpenMobileNav }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const initial = (user?.first_name || user?.username || '?').charAt(0).toUpperCase()

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

      <div className="ml-auto flex items-center gap-2.5">
        <Button size="sm" onClick={() => navigate('/goals/new')}>
          <PlusIcon size={15} />
          <span className="hidden sm:inline">New goal</span>
        </Button>

        <div className="mx-1 hidden h-5 w-px bg-line sm:block" />

        <div className="flex items-center gap-2">
          <span
            className="grid h-7.5 w-7.5 place-items-center rounded-full bg-brand-100 text-[12.5px] font-semibold text-brand-700"
            title={user?.username}
          >
            {initial}
          </span>
          <span className="hidden max-w-32 truncate text-[13px] font-medium text-ink sm:block">
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
