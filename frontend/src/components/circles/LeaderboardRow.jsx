import { motion } from 'framer-motion'
import cn from '../../lib/cn'
import Badge from '../ui/Badge'
import ProgressBar from '../ui/ProgressBar'
import { CrownIcon, FlameIcon } from '../ui/Icons'

const RANK_STYLE = {
  1: 'bg-warning-soft text-warning',
  2: 'bg-surface-muted text-ink-soft',
  3: 'bg-brand-50 text-brand-700',
}

export default function LeaderboardRow({ row, index = 0 }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, delay: Math.min(index * 0.04, 0.2) }}
      className={cn(
        'flex items-center gap-3 rounded-lg px-2.5 py-2.5',
        row.is_you && 'bg-brand-50/60',
      )}
    >
      <span
        className={cn(
          'grid h-7 w-7 shrink-0 place-items-center rounded-full text-[12px] font-semibold',
          RANK_STYLE[row.rank] || 'bg-surface-muted text-ink-muted',
        )}
      >
        {row.rank}
      </span>

      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-100 text-[12.5px] font-semibold text-brand-700">
        {row.name.charAt(0).toUpperCase()}
      </span>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <p className="truncate text-[13.5px] font-medium text-ink">
            {row.name}
            {row.is_you && <span className="text-ink-muted"> (you)</span>}
          </p>
          {row.is_owner && (
            <span title="Circle owner" className="text-warning">
              <CrownIcon size={13} />
            </span>
          )}
        </div>
        <div className="mt-1 flex items-center gap-2">
          <ProgressBar value={row.overall_progress} className="max-w-28" />
          <span className="text-[11.5px] text-ink-muted">{row.overall_progress}%</span>
        </div>
      </div>

      <div className="flex shrink-0 flex-col items-end gap-1">
        <Badge tone={row.completed_this_week > 0 ? 'brand' : 'neutral'}>
          {row.completed_this_week} this week
        </Badge>
        {row.streak_current > 0 && (
          <span className="flex items-center gap-1 text-[11.5px] text-warning">
            <FlameIcon size={12} />
            {row.streak_current}d
          </span>
        )}
      </div>
    </motion.div>
  )
}
