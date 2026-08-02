import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import Badge from '../ui/Badge'
import ProgressBar from '../ui/ProgressBar'
import { formatDate } from '../../lib/format'

export default function GoalProgressCard({ goal, index = 0 }) {
  const complete = goal.progress === 100 && goal.total_tasks > 0

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, delay: Math.min(index * 0.04, 0.2) }}
    >
      <Link
        to={`/goals/${goal.id}`}
        className="block rounded-lg px-2.5 py-2.5 transition-colors hover:bg-surface-muted"
      >
        <div className="flex items-start justify-between gap-3">
          <p className="line-clamp-1 text-[13.5px] font-medium text-ink">{goal.title}</p>
          {complete ? (
            <Badge tone="success">Done</Badge>
          ) : (
            <span className="shrink-0 text-[12.5px] font-semibold tabular-nums text-ink-soft">
              {goal.progress}%
            </span>
          )}
        </div>
        <ProgressBar value={goal.progress} className="mt-2" />
        <div className="mt-1.5 flex items-center justify-between text-[12px] text-ink-muted">
          <span>
            {goal.completed_tasks}/{goal.total_tasks} tasks
          </span>
          {goal.target_date && <span>by {formatDate(goal.target_date)}</span>}
        </div>
      </Link>
    </motion.div>
  )
}
