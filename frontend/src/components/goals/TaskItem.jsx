import { useState } from 'react'
import { motion } from 'framer-motion'
import cn from '../../lib/cn'
import { dueLabel } from '../../lib/format'
import Badge from '../ui/Badge'
import InlineEdit from '../ui/InlineEdit'
import Spinner from '../ui/Spinner'
import { SparklesIcon, TrashIcon } from '../ui/Icons'

function Checkbox({ checked, onChange, label }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={checked}
      aria-label={label}
      onClick={onChange}
      className={cn(
        'mt-0.5 grid h-4.5 w-4.5 shrink-0 place-items-center rounded-[5px] border transition-colors duration-150',
        checked
          ? 'border-success bg-success text-white'
          : 'border-line-strong bg-surface hover:border-brand-500',
      )}
    >
      {checked && (
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
  )
}

export default function TaskItem({
  task,
  onToggle,
  onRename,
  onDueDateChange,
  onDelete,
  onBreakdown,
  breakingDown = false,
  isSubtask = false,
}) {
  const [hovered, setHovered] = useState(false)
  const due = dueLabel(task.due_date)
  const showDue = !task.is_complete && due.days !== null

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.16 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={cn(
        'group flex items-start gap-2.5 rounded-lg px-2 py-1.5 transition-colors',
        'hover:bg-surface-muted',
        isSubtask && 'ml-6 border-l-2 border-line pl-3',
      )}
    >
      <Checkbox
        checked={task.is_complete}
        onChange={() => onToggle(task)}
        label={`Mark "${task.title}" ${task.is_complete ? 'incomplete' : 'complete'}`}
      />

      <div className="min-w-0 flex-1">
        <InlineEdit
          value={task.title}
          onCommit={(title) => onRename(task, title)}
          ariaLabel="Task title"
          className={cn(
            'text-[13.5px] leading-relaxed',
            task.is_complete && 'text-ink-muted line-through',
          )}
          inputClassName="text-[13.5px]"
        />
      </div>

      <div className="flex shrink-0 items-center gap-1.5">
        {showDue && (
          <Badge tone={due.tone} className="hidden sm:inline-flex">
            {due.text}
          </Badge>
        )}

        <input
          type="date"
          value={task.due_date || ''}
          onChange={(e) => onDueDateChange(task, e.target.value || null)}
          aria-label="Task due date"
          className={cn(
            'w-[7.5rem] rounded-md border border-line bg-surface px-1.5 py-0.5 text-[12px] text-ink-soft',
            'transition-opacity outline-none focus:border-brand-500',
            hovered ? 'opacity-100' : 'opacity-0 focus:opacity-100',
          )}
        />

        {onBreakdown && !task.is_complete && (
          <button
            type="button"
            onClick={() => onBreakdown(task)}
            disabled={breakingDown}
            title="Break this task into smaller steps"
            aria-label="Break this task down"
            className={cn(
              'rounded-md p-1.5 text-ink-muted transition-colors hover:bg-brand-50 hover:text-brand-600',
              'disabled:opacity-50',
              hovered || breakingDown ? 'opacity-100' : 'opacity-0',
            )}
          >
            {breakingDown ? <Spinner size={14} /> : <SparklesIcon size={14} />}
          </button>
        )}

        <button
          type="button"
          onClick={() => onDelete(task)}
          aria-label="Delete task"
          className={cn(
            'rounded-md p-1.5 text-ink-muted transition-colors hover:bg-danger-soft hover:text-danger',
            hovered ? 'opacity-100' : 'opacity-0',
          )}
        >
          <TrashIcon size={14} />
        </button>
      </div>
    </motion.div>
  )
}
