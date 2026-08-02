import { useMemo } from 'react'
import { AnimatePresence } from 'framer-motion'
import Card, { CardHeader } from '../ui/Card'
import EmptyState from '../ui/EmptyState'
import TaskRow from './TaskRow'
import { formatDayHeading } from '../../lib/format'
import { CalendarIcon } from '../ui/Icons'

/** Group tasks by due date, preserving the server's chronological order. */
function groupByDate(tasks) {
  const groups = new Map()
  tasks.forEach((task) => {
    const key = task.due_date || 'none'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(task)
  })
  return [...groups.entries()]
}

export default function DeadlineList({ tasks, onToggle, title = 'Next 7 days' }) {
  const groups = useMemo(() => groupByDate(tasks), [tasks])

  return (
    <Card>
      <CardHeader
        title={title}
        subtitle={tasks.length ? `${tasks.length} upcoming` : undefined}
      />

      {tasks.length === 0 ? (
        <EmptyState
          icon={CalendarIcon}
          title="No deadlines this week"
          message="Nothing is due in the next seven days."
          className="py-9"
        />
      ) : (
        <div className="px-3 pb-3">
          {groups.map(([date, items]) => (
            <div key={date} className="mb-1">
              <p className="px-2 pt-2 pb-1 text-[11.5px] font-semibold tracking-wide text-ink-muted uppercase">
                {formatDayHeading(date === 'none' ? null : date)}
              </p>
              <AnimatePresence initial={false}>
                {items.map((task) => (
                  <TaskRow key={task.id} task={task} onToggle={onToggle} showDue={false} />
                ))}
              </AnimatePresence>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
