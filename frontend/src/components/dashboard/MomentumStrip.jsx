import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import cn from '../../lib/cn'
import api from '../../lib/api'
import { FlameIcon, TimerIcon } from '../ui/Icons'

const LEVELS = ['bg-line', 'bg-brand-200', 'bg-brand-400', 'bg-brand-500', 'bg-brand-600']
const RECENT_DAYS = 21

/** Compact streak + focus summary for the top of the dashboard. */
export default function MomentumStrip() {
  const [momentum, setMomentum] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .get('/momentum/')
      .then(({ data }) => !cancelled && setMomentum(data))
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  if (!momentum) return null

  const { streak, focus, heatmap } = momentum
  const recent = heatmap.slice(-RECENT_DAYS)
  const alive = streak.current > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24 }}
      className="flex flex-wrap items-center gap-x-6 gap-y-4 rounded-card border border-line bg-surface px-4 py-3.5 shadow-card"
    >
      <div className="flex items-center gap-2.5">
        <span
          className={cn(
            'grid h-9 w-9 shrink-0 place-items-center rounded-lg',
            alive ? 'bg-warning-soft text-warning' : 'bg-surface-muted text-ink-muted',
          )}
        >
          <FlameIcon size={18} />
        </span>
        <div>
          <p className="text-[15px] leading-none font-semibold tabular-nums text-ink">
            {streak.current} day{streak.current === 1 ? '' : 's'}
          </p>
          <p className="mt-1 text-[12px] text-ink-muted">
            {streak.active_today ? 'Active today' : alive ? 'Keep it alive' : 'No streak yet'}
          </p>
        </div>
      </div>

      <div className="hidden h-8 w-px bg-line sm:block" />

      <div className="flex items-center gap-2.5">
        <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-brand-50 text-brand-600">
          <TimerIcon size={18} />
        </span>
        <div>
          <p className="text-[15px] leading-none font-semibold tabular-nums text-ink">
            {focus.today_minutes} min
          </p>
          <p className="mt-1 text-[12px] text-ink-muted">Focused today</p>
        </div>
      </div>

      <div className="ml-auto flex items-center gap-3">
        <div className="hidden items-end gap-[3px] sm:flex">
          {recent.map((day) => (
            <span
              key={day.date}
              title={`${day.date}: ${day.tasks} task${day.tasks === 1 ? '' : 's'}, ${day.focus_minutes} min`}
              className={cn('h-6 w-2 rounded-[2px]', LEVELS[day.level])}
            />
          ))}
        </div>
        <Link
          to="/focus"
          className="rounded-lg border border-line px-3 py-1.5 text-[13px] font-medium text-ink-soft transition-colors hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700"
        >
          Focus
        </Link>
      </div>
    </motion.div>
  )
}
