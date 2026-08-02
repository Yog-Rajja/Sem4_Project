import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import cn from '../../lib/cn'
import { dueLabel } from '../../lib/format'
import Badge from '../ui/Badge'

/** Compact, read-mostly task row used on the dashboard and task list. */
export default function TaskRow({ task, onToggle, showDue = true, showGoal = true }) {
  const due = dueLabel(task.due_date)

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.16 }}
      className="flex items-start gap-2.5 rounded-lg px-2 py-2 transition-colors hover:bg-surface-muted"
    >
      <button
        type="button"
        role="checkbox"
        aria-checked={task.is_complete}
        aria-label={`Mark "${task.title}" ${task.is_complete ? 'incomplete' : 'complete'}`}
        onClick={() => onToggle(task)}
        className={cn(
          'mt-0.5 grid h-4.5 w-4.5 shrink-0 place-items-center rounded-[5px] border transition-colors',
          task.is_complete
            ? 'border-success bg-success text-white'
            : 'border-line-strong bg-surface hover:border-brand-500',
        )}
      >
        {task.is_complete && (
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="m5 12.5 4.5 4.5L19 7"
              stroke="currentColor"
              strokeWidth="3"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        )}
      </button>

      <div className="min-w-0 flex-1">
        <p
          className={cn(
            'text-[13.5px] leading-snug',
            task.is_complete && 'text-ink-muted line-through',
          )}
        >
          {task.title}
        </p>
        {showGoal && task.goal_title && (
          <Link
            to={`/goals/${task.goal_id}`}
            className="mt-0.5 inline-block truncate text-[12px] text-ink-muted transition-colors hover:text-brand-600"
          >
            {task.goal_title}
          </Link>
        )}
      </div>

      {showDue && !task.is_complete && task.due_date && (
        <Badge tone={due.tone} className="mt-0.5 shrink-0">
          {due.text}
        </Badge>
      )}
    </motion.div>
  )
}
