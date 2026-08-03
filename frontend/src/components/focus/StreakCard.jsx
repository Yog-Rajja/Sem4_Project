import { useMemo } from 'react'
import { motion } from 'framer-motion'
import cn from '../../lib/cn'
import Card, { CardHeader } from '../ui/Card'
import Spinner from '../ui/Spinner'
import { FlameIcon } from '../ui/Icons'

// Level 0 is an empty day; 1-4 step up with how much got done.
const LEVELS = [
  'bg-line',
  'bg-brand-200',
  'bg-brand-400',
  'bg-brand-500',
  'bg-brand-600',
]

function Stat({ label, value, accent }) {
  return (
    <div>
      <p className="text-[11.5px] font-medium tracking-wide text-ink-muted uppercase">
        {label}
      </p>
      <p
        className={cn(
          'mt-1 text-xl font-semibold tabular-nums',
          accent ? 'text-brand-600' : 'text-ink',
        )}
      >
        {value}
      </p>
    </div>
  )
}

export default function StreakCard({ momentum, loading }) {
  // The API returns a flat run of days; chunk it into calendar weeks.
  const weeks = useMemo(() => {
    if (!momentum?.heatmap) return []
    const out = []
    for (let i = 0; i < momentum.heatmap.length; i += 7) {
      out.push(momentum.heatmap.slice(i, i + 7))
    }
    return out
  }, [momentum])

  if (loading || !momentum) {
    return (
      <Card>
        <div className="grid place-items-center py-14 text-brand-600">
          <Spinner size={18} />
        </div>
      </Card>
    )
  }

  const { streak, focus } = momentum
  const alive = streak.current > 0

  return (
    <Card>
      <CardHeader
        title="Momentum"
        subtitle="A day counts when you finish a task or log a focus session"
      />

      <div className="px-5 pb-4">
        <div className="flex items-center gap-3">
          <span
            className={cn(
              'grid h-11 w-11 shrink-0 place-items-center rounded-xl',
              alive ? 'bg-warning-soft text-warning' : 'bg-surface-muted text-ink-muted',
            )}
          >
            <FlameIcon size={21} />
          </span>
          <div>
            <p className="text-2xl leading-none font-semibold tabular-nums text-ink">
              {streak.current}
              <span className="ml-1.5 text-[13px] font-medium text-ink-muted">
                day{streak.current === 1 ? '' : 's'}
              </span>
            </p>
            <p className="mt-1 text-[12.5px] text-ink-muted">
              {streak.active_today
                ? 'Already active today'
                : alive
                  ? 'Keep it alive before midnight'
                  : 'Start a new streak today'}
            </p>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-3 gap-4">
          <Stat label="Longest" value={`${streak.longest}d`} />
          <Stat label="Today" value={`${focus.today_minutes}m`} accent />
          <Stat label="This week" value={`${focus.week_minutes}m`} />
        </div>

        <div className="mt-5">
          <div className="flex gap-[3px] overflow-x-auto pb-1 scrollbar-thin">
            {weeks.map((week, weekIndex) => (
              <div key={weekIndex} className="flex flex-col gap-[3px]">
                {week.map((day) => (
                  <motion.span
                    key={day.date}
                    initial={{ opacity: 0, scale: 0.7 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.18, delay: Math.min(weekIndex * 0.008, 0.15) }}
                    title={`${day.date}: ${day.tasks} task${day.tasks === 1 ? '' : 's'}, ${day.focus_minutes} min focus`}
                    className={cn('h-3 w-3 rounded-[3px]', LEVELS[day.level])}
                  />
                ))}
              </div>
            ))}
          </div>
          <div className="mt-2 flex items-center justify-end gap-1.5 text-[11px] text-ink-muted">
            <span>Less</span>
            {LEVELS.map((level) => (
              <span key={level} className={cn('h-2.5 w-2.5 rounded-[3px]', level)} />
            ))}
            <span>More</span>
          </div>
        </div>
      </div>
    </Card>
  )
}
