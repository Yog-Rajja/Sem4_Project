import { AnimatePresence } from 'framer-motion'
import Card, { CardHeader } from '../ui/Card'
import EmptyState from '../ui/EmptyState'
import TaskRow from './TaskRow'
import { CheckSquareIcon } from '../ui/Icons'

export default function TodayList({ tasks, overdue = [], onToggle }) {
  const hasAnything = tasks.length > 0 || overdue.length > 0

  return (
    <Card>
      <CardHeader
        title="Today"
        subtitle={
          hasAnything
            ? `${tasks.length} due today${overdue.length ? ` · ${overdue.length} overdue` : ''}`
            : undefined
        }
      />

      {!hasAnything ? (
        <EmptyState
          icon={CheckSquareIcon}
          title="Nothing due today"
          message="You're clear. Pull something forward from this week, or enjoy the breathing room."
          className="py-9"
        />
      ) : (
        <div className="px-3 pb-3">
          {overdue.length > 0 && (
            <>
              <p className="px-2 pt-1 pb-1.5 text-[11.5px] font-semibold tracking-wide text-danger uppercase">
                Overdue
              </p>
              <AnimatePresence initial={false}>
                {overdue.map((task) => (
                  <TaskRow key={task.id} task={task} onToggle={onToggle} />
                ))}
              </AnimatePresence>
            </>
          )}

          {tasks.length > 0 && (
            <>
              {overdue.length > 0 && (
                <p className="px-2 pt-3 pb-1.5 text-[11.5px] font-semibold tracking-wide text-ink-muted uppercase">
                  Due today
                </p>
              )}
              <AnimatePresence initial={false}>
                {tasks.map((task) => (
                  <TaskRow key={task.id} task={task} onToggle={onToggle} showDue={false} />
                ))}
              </AnimatePresence>
            </>
          )}
        </div>
      )}
    </Card>
  )
}
