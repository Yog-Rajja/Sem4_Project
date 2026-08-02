import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import Badge from '../ui/Badge'
import ProgressBar from '../ui/ProgressBar'
import { formatDate } from '../../lib/format'
import { ChevronRightIcon } from '../ui/Icons'

export default function GoalCard({ goal, index = 0 }) {
  const complete = goal.progress === 100 && goal.total_tasks > 0

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.24, delay: Math.min(index * 0.04, 0.2) }}
    >
      <Link
        to={`/goals/${goal.id}`}
        className="group flex h-full flex-col rounded-card border border-line bg-surface p-4 shadow-card transition-all duration-150 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-pop"
      >
        <div className="flex items-start justify-between gap-3">
          <h3 className="line-clamp-2 text-[14.5px] leading-snug font-semibold tracking-[-0.01em] text-ink">
            {goal.title}
          </h3>
          <ChevronRightIcon
            size={16}
            className="mt-0.5 shrink-0 text-ink-muted transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-brand-600"
          />
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {complete ? (
            <Badge tone="success">Complete</Badge>
          ) : (
            <Badge tone="brand">{goal.progress}% done</Badge>
          )}
          <Badge>
            {goal.milestone_count} milestone{goal.milestone_count === 1 ? '' : 's'}
          </Badge>
        </div>

        <div className="mt-auto pt-4">
          <ProgressBar value={goal.progress} />
          <div className="mt-2 flex items-center justify-between text-[12.5px] text-ink-muted">
            <span>
              {goal.completed_tasks}/{goal.total_tasks} tasks
            </span>
            {goal.target_date && <span>by {formatDate(goal.target_date)}</span>}
          </div>
        </div>
      </Link>
    </motion.div>
  )
}
