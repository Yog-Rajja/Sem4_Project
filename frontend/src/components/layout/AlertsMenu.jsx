import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import cn from '../../lib/cn'
import api from '../../lib/api'
import { AlertIcon, BellIcon, CheckSquareIcon, ClockIcon, FlameIcon } from '../ui/Icons'

const SEVERITY = {
  critical: { icon: AlertIcon, tone: 'text-danger', bg: 'bg-danger-soft' },
  warning: { icon: ClockIcon, tone: 'text-warning', bg: 'bg-warning-soft' },
  info: { icon: BellIcon, tone: 'text-brand-600', bg: 'bg-brand-50' },
  success: { icon: CheckSquareIcon, tone: 'text-success', bg: 'bg-success-soft' },
}

const REFRESH_MS = 60_000

export default function AlertsMenu() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [alerts, setAlerts] = useState([])
  const [unread, setUnread] = useState(0)
  const wrapRef = useRef(null)

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/alerts/')
      setAlerts(data.alerts)
      setUnread(data.unread)
    } catch {
      // The bell is ambient — a failure here should never interrupt the user.
    }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => clearInterval(id)
  }, [load])

  // Refresh whenever it's opened, so the badge is never showing stale counts.
  useEffect(() => {
    if (open) load()
  }, [open, load])

  useEffect(() => {
    if (!open) return
    const onClick = (event) => {
      if (!wrapRef.current?.contains(event.target)) setOpen(false)
    }
    const onKey = (event) => event.key === 'Escape' && setOpen(false)
    document.addEventListener('mousedown', onClick)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClick)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={wrapRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label={unread ? `Alerts, ${unread} needing attention` : 'Alerts'}
        aria-expanded={open}
        className="relative rounded-lg p-2 text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
      >
        <BellIcon size={17} />
        {unread > 0 && (
          <span className="absolute top-1 right-1 grid h-4 min-w-4 place-items-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.99 }}
            transition={{ duration: 0.15 }}
            className="absolute right-0 z-50 mt-2 w-[21rem] overflow-hidden rounded-xl border border-line bg-surface shadow-pop"
          >
            <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
              <p className="text-[13px] font-semibold text-ink">Alerts</p>
              <span className="text-[12px] text-ink-muted">
                {alerts.length || 'None'}
              </span>
            </div>

            <div className="max-h-96 overflow-y-auto scrollbar-thin">
              {alerts.length === 0 ? (
                <div className="px-4 py-8 text-center">
                  <FlameIcon size={20} className="mx-auto mb-2 text-ink-muted" />
                  <p className="text-[13px] font-medium text-ink">All clear</p>
                  <p className="mt-1 text-[12px] text-ink-muted">
                    Nothing overdue, nothing slipping.
                  </p>
                </div>
              ) : (
                alerts.map((alert) => {
                  const style = SEVERITY[alert.severity] || SEVERITY.info
                  const Icon = style.icon
                  return (
                    <button
                      key={alert.id}
                      type="button"
                      onClick={() => {
                        setOpen(false)
                        navigate(alert.path)
                      }}
                      className="flex w-full items-start gap-2.5 border-b border-line px-4 py-3 text-left transition-colors last:border-0 hover:bg-surface-muted"
                    >
                      <span
                        className={cn(
                          'mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg',
                          style.bg,
                          style.tone,
                        )}
                      >
                        <Icon size={14} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-[13px] font-medium text-ink">
                          {alert.title}
                        </span>
                        <span className="mt-0.5 block text-[12px] leading-relaxed text-ink-muted">
                          {alert.message}
                        </span>
                        {alert.action && (
                          <span className="mt-1 block text-[12px] font-medium text-brand-600">
                            {alert.action} →
                          </span>
                        )}
                      </span>
                    </button>
                  )
                })
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
