import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence } from 'framer-motion'
import PageShell from '../components/layout/PageShell'
import TaskRow from '../components/dashboard/TaskRow'
import Card from '../components/ui/Card'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import { Select } from '../components/ui/Input'
import Spinner from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import { CheckSquareIcon } from '../components/ui/Icons'
import api, { errorMessage } from '../lib/api'
import { unwrapList } from '../lib/list'
import { formatDayHeading } from '../lib/format'

const STATUS_OPTIONS = [
  { value: 'pending', label: 'Pending' },
  { value: 'complete', label: 'Completed' },
  { value: 'all', label: 'All statuses' },
]

const DUE_OPTIONS = [
  { value: 'all', label: 'Any time' },
  { value: 'overdue', label: 'Overdue' },
  { value: 'today', label: 'Due today' },
  { value: 'week', label: 'Next 7 days' },
]

export default function Tasks() {
  const toast = useToast()

  const [tasks, setTasks] = useState([])
  const [goals, setGoals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [confirmTask, setConfirmTask] = useState(null)
  const [deleting, setDeleting] = useState(false)

  const [goalFilter, setGoalFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('pending')
  const [dueFilter, setDueFilter] = useState('all')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    const params = {}
    if (goalFilter !== 'all') params.goal = goalFilter
    if (statusFilter !== 'all') params.status = statusFilter
    if (dueFilter !== 'all') params.due = dueFilter

    try {
      const [taskRes, goalRes] = await Promise.all([
        api.get('/tasks/', { params }),
        api.get('/goals/'),
      ])
      setTasks(unwrapList(taskRes.data))
      setGoals(unwrapList(goalRes.data))
    } catch (err) {
      setError(errorMessage(err, 'Could not load your tasks.'))
    } finally {
      setLoading(false)
    }
  }, [goalFilter, statusFilter, dueFilter])

  useEffect(() => {
    load()
  }, [load])

  const toggle = async (task) => {
    const is_complete = !task.is_complete
    setTasks((current) =>
      current.map((t) => (t.id === task.id ? { ...t, is_complete } : t)),
    )
    try {
      await api.patch(`/tasks/${task.id}/`, { is_complete })
      // A pending-only view should drop the task once it's ticked off.
      if (statusFilter !== 'all') {
        setTasks((current) => current.filter((t) => t.id !== task.id))
      }
    } catch (err) {
      toast.error(errorMessage(err, 'Could not update that task.'))
      load()
    }
  }

  async function confirmDelete() {
    setDeleting(true)
    try {
      await api.delete(`/tasks/${confirmTask.id}/`)
      setTasks((current) => current.filter((t) => t.id !== confirmTask.id))
      setConfirmTask(null)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete that task.'))
    } finally {
      setDeleting(false)
    }
  }

  // Group by due date so a long cross-goal list stays scannable.
  const groups = useMemo(() => {
    const map = new Map()
    tasks.forEach((task) => {
      const key = task.due_date || 'none'
      if (!map.has(key)) map.set(key, [])
      map.get(key).push(task)
    })
    return [...map.entries()]
  }, [tasks])

  const filtersActive =
    goalFilter !== 'all' || statusFilter !== 'pending' || dueFilter !== 'all'

  return (
    <PageShell
      title="Tasks"
      subtitle="Everything across all your goals, in one list."
    >
      <Card className="mb-3 flex flex-wrap items-center gap-2 p-3">
        <Select
          value={goalFilter}
          onChange={(e) => setGoalFilter(e.target.value)}
          aria-label="Filter by goal"
          className="w-auto min-w-44"
        >
          <option value="all">All goals</option>
          {goals.map((goal) => (
            <option key={goal.id} value={goal.id}>
              {goal.title}
            </option>
          ))}
        </Select>

        <Select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          aria-label="Filter by status"
          className="w-auto min-w-36"
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>

        <Select
          value={dueFilter}
          onChange={(e) => setDueFilter(e.target.value)}
          aria-label="Filter by due date"
          className="w-auto min-w-36"
        >
          {DUE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>

        {filtersActive && (
          <button
            type="button"
            onClick={() => {
              setGoalFilter('all')
              setStatusFilter('pending')
              setDueFilter('all')
            }}
            className="ml-auto text-[13px] font-medium text-ink-muted transition-colors hover:text-ink"
          >
            Reset filters
          </button>
        )}
      </Card>

      {loading ? (
        <div className="grid place-items-center py-20 text-brand-600">
          <Spinner size={24} />
        </div>
      ) : error ? (
        <Card>
          <ErrorState message={error} onRetry={load} />
        </Card>
      ) : tasks.length === 0 ? (
        <Card>
          <EmptyState
            icon={CheckSquareIcon}
            title={filtersActive ? 'No tasks match these filters' : 'No tasks yet'}
            message={
              filtersActive
                ? 'Try widening the filters to see more of your work.'
                : 'Create a goal and your roadmap tasks will appear here.'
            }
          />
        </Card>
      ) : (
        <Card className="p-3">
          <p className="px-2 pb-1 text-[12.5px] text-ink-muted">
            {tasks.length} task{tasks.length === 1 ? '' : 's'}
          </p>
          {groups.map(([date, items]) => (
            <div key={date} className="mb-1">
              <p className="px-2 pt-2 pb-1 text-[11.5px] font-semibold tracking-wide text-ink-muted uppercase">
                {formatDayHeading(date === 'none' ? null : date)}
              </p>
              <AnimatePresence initial={false}>
                {items.map((task) => (
                  <div key={task.id} className="group/row relative">
                    <TaskRow task={task} onToggle={toggle} />
                    <button
                      type="button"
                      onClick={() => setConfirmTask(task)}
                      aria-label="Delete task"
                      className="absolute top-1/2 right-2 -translate-y-1/2 rounded-md px-2 py-1 text-[12px] font-medium text-ink-muted opacity-0 transition-opacity group-hover/row:opacity-100 hover:text-danger"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </AnimatePresence>
            </div>
          ))}
        </Card>
      )}

      <ConfirmDialog
        open={Boolean(confirmTask)}
        onClose={() => !deleting && setConfirmTask(null)}
        onConfirm={confirmDelete}
        loading={deleting}
        title="Delete this task?"
        message={`“${confirmTask?.title}” will be permanently removed.`}
      />
    </PageShell>
  )
}
