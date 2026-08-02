import { useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import cn from '../../lib/cn'
import { formatDate } from '../../lib/format'
import Badge from '../ui/Badge'
import Button from '../ui/Button'
import InlineEdit from '../ui/InlineEdit'
import ProgressBar from '../ui/ProgressBar'
import ResourceList from './ResourceList'
import TaskItem from './TaskItem'
import {
  ArrowDownIcon,
  ArrowUpIcon,
  ChevronDownIcon,
  PlusIcon,
  TrashIcon,
} from '../ui/Icons'

export default function MilestoneCard({
  milestone,
  index,
  isFirst,
  isLast,
  onRename,
  onDateChange,
  onQueryChange,
  onToggleComplete,
  onDelete,
  onMove,
  onAddTask,
  taskHandlers,
  onFetchResources,
  resourcesLoading,
  resourcesWarning,
  breakingDownTaskId,
}) {
  const [open, setOpen] = useState(true)
  const [addingTask, setAddingTask] = useState(false)
  const [newTaskTitle, setNewTaskTitle] = useState('')

  // Subtasks render nested under their parent rather than as siblings.
  const { roots, childrenByParent } = useMemo(() => {
    const tasks = milestone.tasks || []
    const map = new Map()
    tasks.forEach((t) => {
      if (t.parent) {
        if (!map.has(t.parent)) map.set(t.parent, [])
        map.get(t.parent).push(t)
      }
    })
    return { roots: tasks.filter((t) => !t.parent), childrenByParent: map }
  }, [milestone.tasks])

  const total = (milestone.tasks || []).length
  const done = (milestone.tasks || []).filter((t) => t.is_complete).length
  const progress = total ? Math.round((done * 100) / total) : 0
  const complete = milestone.is_complete || (total > 0 && done === total)

  function submitNewTask(e) {
    e.preventDefault()
    const title = newTaskTitle.trim()
    if (!title) return
    onAddTask(milestone, title)
    setNewTaskTitle('')
    setAddingTask(false)
  }

  return (
    <motion.section
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
      className="overflow-hidden rounded-card border border-line bg-surface shadow-card"
    >
      <header className="flex items-start gap-3 px-4 py-3.5">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label={open ? 'Collapse milestone' : 'Expand milestone'}
          className="mt-0.5 rounded-md p-0.5 text-ink-muted transition-colors hover:bg-surface-muted hover:text-ink"
        >
          <motion.span
            animate={{ rotate: open ? 0 : -90 }}
            transition={{ duration: 0.18 }}
            className="block"
          >
            <ChevronDownIcon size={16} />
          </motion.span>
        </button>

        <span
          className={cn(
            'mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md text-[12px] font-semibold',
            complete ? 'bg-success-soft text-success' : 'bg-brand-100 text-brand-700',
          )}
        >
          {index + 1}
        </span>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <InlineEdit
              value={milestone.title}
              onCommit={(title) => onRename(milestone, title)}
              ariaLabel="Milestone title"
              className={cn(
                'text-[14.5px] font-semibold tracking-[-0.01em]',
                complete && 'text-ink-muted line-through',
              )}
              inputClassName="text-[14.5px] font-semibold"
            />
            {complete && <Badge tone="success">Done</Badge>}
          </div>

          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[12.5px] text-ink-muted">
            <label className="flex items-center gap-1.5">
              <span>Target</span>
              <input
                type="date"
                value={milestone.target_date || ''}
                onChange={(e) => onDateChange(milestone, e.target.value || null)}
                aria-label="Milestone target date"
                className="rounded-md border border-line bg-surface px-1.5 py-0.5 text-[12px] outline-none focus:border-brand-500"
              />
            </label>
            <span aria-hidden="true">·</span>
            <span>
              {done}/{total} task{total === 1 ? '' : 's'}
            </span>
            {milestone.target_date && (
              <span className="hidden sm:inline">
                · by {formatDate(milestone.target_date)}
              </span>
            )}
          </div>

          <ProgressBar value={progress} className="mt-2.5 max-w-sm" />
        </div>

        <div className="flex shrink-0 items-center gap-0.5">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onToggleComplete(milestone)}
            title={complete ? 'Mark milestone as not done' : 'Mark milestone done'}
          >
            {complete ? 'Reopen' : 'Complete'}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onMove(index, -1)}
            disabled={isFirst}
            aria-label="Move milestone up"
          >
            <ArrowUpIcon size={15} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onMove(index, 1)}
            disabled={isLast}
            aria-label="Move milestone down"
          >
            <ArrowDownIcon size={15} />
          </Button>
          <Button
            variant="dangerGhost"
            size="icon"
            onClick={() => onDelete(milestone)}
            aria-label="Delete milestone"
          >
            <TrashIcon size={15} />
          </Button>
        </div>
      </header>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="border-t border-line px-3 py-2">
              <AnimatePresence initial={false}>
                {roots.map((task) => (
                  <div key={task.id}>
                    <TaskItem
                      task={task}
                      breakingDown={breakingDownTaskId === task.id}
                      {...taskHandlers}
                    />
                    {(childrenByParent.get(task.id) || []).map((subtask) => (
                      <TaskItem
                        key={subtask.id}
                        task={subtask}
                        isSubtask
                        {...taskHandlers}
                        onBreakdown={null}
                      />
                    ))}
                  </div>
                ))}
              </AnimatePresence>

              {total === 0 && !addingTask && (
                <p className="px-2 py-2 text-[13px] text-ink-muted">
                  No tasks yet in this milestone.
                </p>
              )}

              {addingTask ? (
                <form onSubmit={submitNewTask} className="flex items-center gap-2 px-2 py-1.5">
                  <input
                    autoFocus
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                    onBlur={() => !newTaskTitle.trim() && setAddingTask(false)}
                    onKeyDown={(e) => e.key === 'Escape' && setAddingTask(false)}
                    placeholder="What needs doing?"
                    aria-label="New task title"
                    className="h-8 flex-1 rounded-lg border border-brand-500 bg-surface px-2.5 text-[13.5px] outline-none ring-3 ring-brand-500/15"
                  />
                  <Button type="submit" size="sm">
                    Add
                  </Button>
                </form>
              ) : (
                <Button
                  variant="ghost"
                  size="sm"
                  className="ml-1"
                  onClick={() => setAddingTask(true)}
                >
                  <PlusIcon size={14} />
                  Add task
                </Button>
              )}
            </div>

            <div className="border-t border-line bg-surface-muted px-3 py-2.5">
              <ResourceList
                resources={milestone.resources || []}
                loading={resourcesLoading}
                warning={resourcesWarning}
                searchQuery={milestone.search_query}
                onFetch={() => onFetchResources(milestone)}
              />
              {(milestone.resources || []).length > 0 && (
                <div className="mt-2 flex items-center gap-1.5 px-1 text-[12px] text-ink-muted">
                  <span className="shrink-0">Topic</span>
                  <InlineEdit
                    value={milestone.search_query || ''}
                    onCommit={(query) => onQueryChange(milestone, query)}
                    placeholder="Set a topic"
                    ariaLabel="Resource search topic"
                    className="text-[12px]"
                    inputClassName="text-[12px]"
                  />
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  )
}
