import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import cn from '../../lib/cn'
import { dueLabel } from '../../lib/format'
import Badge from '../ui/Badge'
import confetti from 'canvas-confetti'

/** Compact, read-mostly task row used on the dashboard and task list. */
export default function TaskRow({ task, onToggle, showDue = true, showGoal = true }) {
  const due = dueLabel(task.due_date)

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
      className="flex items-start gap-3 rounded-xl px-2 py-2.5 transition-colors hover:bg-surface-muted"
    >
      <motion.button
        type="button"
        role="checkbox"
        aria-checked={task.is_complete}
        aria-label={`Mark "${task.title}" ${task.is_complete ? 'incomplete' : 'complete'}`}
        whileHover={{ scale: 1.15 }}
        whileTap={{ scale: 0.85 }}
        onClick={() => {
          if (!task.is_complete) {
            confetti({
              particleCount: 50,
              spread: 60,
              origin: { y: 0.8 },
              colors: ['#FF6B6B', '#FFD93D', '#5AC8FA', '#9B6DFF', '#61E8B2']
            })
          }
          onToggle(task)
        }}
        className={cn(
          'mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md border-2 transition-colors duration-300',
          task.is_complete
            ? 'border-brand-500 bg-brand-500 text-white shadow-glow'
            : 'border-line-strong bg-surface hover:border-brand-400',
        )}
      >
        <AnimatePresence>
          {task.is_complete && (
            <motion.svg
              initial={{ scale: 0, rotate: -45 }}
              animate={{ scale: 1, rotate: 0 }}
              exit={{ scale: 0 }}
              transition={{ type: "spring", stiffness: 500, damping: 25 }}
              width="12" height="12" viewBox="0 0 24 24" fill="none" aria-hidden="true"
            >
              <path
                d="m5 12.5 4.5 4.5L19 7"
                stroke="currentColor"
                strokeWidth="3.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </motion.svg>
          )}
        </AnimatePresence>
      </motion.button>

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
