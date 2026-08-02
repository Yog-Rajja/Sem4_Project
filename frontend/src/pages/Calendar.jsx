import { useCallback, useEffect, useMemo, useState } from 'react'
import { addDays, format, isSameDay, parseISO, startOfWeek } from 'date-fns'
import { AnimatePresence, motion } from 'framer-motion'
import PageShell from '../components/layout/PageShell'
import TaskRow from '../components/dashboard/TaskRow'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import Spinner from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import { CalendarIcon } from '../components/ui/Icons'
import cn from '../lib/cn'
import api, { errorMessage } from '../lib/api'
import { unwrapList } from '../lib/list'

const WEEK_LENGTH = 7

/**
 * Deliberately a week *list*, not a drag-and-drop grid: seven stacked day
 * sections, which reads well on a phone and needs no layout maths.
 */
export default function Calendar() {
  const toast = useToast()

  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [weekOffset, setWeekOffset] = useState(0)

  const weekStart = useMemo(
    () => addDays(startOfWeek(new Date(), { weekStartsOn: 1 }), weekOffset * WEEK_LENGTH),
    [weekOffset],
  )

  const days = useMemo(
    () => Array.from({ length: WEEK_LENGTH }, (_, i) => addDays(weekStart, i)),
    [weekStart],
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/tasks/', { params: { status: 'all' } })
      setTasks(unwrapList(data).filter((t) => t.due_date))
    } catch (err) {
      setError(errorMessage(err, 'Could not load your calendar.'))
    } finally {
      setLoading(false)
    }
  }, [])

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
    } catch (err) {
      toast.error(errorMessage(err, 'Could not update that task.'))
      load()
    }
  }

  const byDay = useMemo(
    () =>
      days.map((day) => ({
        day,
        tasks: tasks.filter((t) => isSameDay(parseISO(t.due_date), day)),
      })),
    [days, tasks],
  )

  const weekTotal = byDay.reduce((sum, d) => sum + d.tasks.length, 0)
  const rangeLabel = `${format(weekStart, 'd MMM')} – ${format(addDays(weekStart, 6), 'd MMM yyyy')}`

  return (
    <PageShell
      title="Calendar"
      subtitle={`${rangeLabel} · ${weekTotal} task${weekTotal === 1 ? '' : 's'}`}
      actions={
        <div className="flex items-center gap-1.5">
          <Button variant="secondary" size="sm" onClick={() => setWeekOffset((w) => w - 1)}>
            ← Prev
          </Button>
          {weekOffset !== 0 && (
            <Button variant="ghost" size="sm" onClick={() => setWeekOffset(0)}>
              This week
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={() => setWeekOffset((w) => w + 1)}>
            Next →
          </Button>
        </div>
      }
    >
      {loading ? (
        <div className="grid place-items-center py-20 text-brand-600">
          <Spinner size={24} />
        </div>
      ) : error ? (
        <Card>
          <ErrorState message={error} onRetry={load} />
        </Card>
      ) : weekTotal === 0 ? (
        <Card>
          <EmptyState
            icon={CalendarIcon}
            title="Nothing scheduled this week"
            message="Tasks with a due date in this week will show up here, grouped by day."
          />
        </Card>
      ) : (
        <div className="space-y-2">
          {byDay.map(({ day, tasks: dayTasks }, index) => {
            const today = isSameDay(day, new Date())
            return (
              <motion.div
                key={day.toISOString()}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: Math.min(index * 0.03, 0.18) }}
              >
                <Card
                  className={cn(
                    'overflow-hidden',
                    today && 'border-brand-200 ring-1 ring-brand-100',
                  )}
                >
                  <div
                    className={cn(
                      'flex items-baseline gap-2.5 px-4 py-2.5',
                      today ? 'bg-brand-50' : 'bg-surface-muted',
                    )}
                  >
                    <span
                      className={cn(
                        'text-[13px] font-semibold',
                        today ? 'text-brand-700' : 'text-ink',
                      )}
                    >
                      {format(day, 'EEEE')}
                    </span>
                    <span className="text-[12.5px] text-ink-muted">
                      {format(day, 'd MMM')}
                    </span>
                    {today && (
                      <span className="rounded-full bg-brand-600 px-1.5 py-0.5 text-[10.5px] font-semibold text-white">
                        Today
                      </span>
                    )}
                    <span className="ml-auto text-[12px] text-ink-muted">
                      {dayTasks.length || 'No'} task{dayTasks.length === 1 ? '' : 's'}
                    </span>
                  </div>

                  {dayTasks.length > 0 && (
                    <div className="px-3 py-2">
                      <AnimatePresence initial={false}>
                        {dayTasks.map((task) => (
                          <TaskRow
                            key={task.id}
                            task={task}
                            onToggle={toggle}
                            showDue={false}
                          />
                        ))}
                      </AnimatePresence>
                    </div>
                  )}
                </Card>
              </motion.div>
            )
          })}
        </div>
      )}
    </PageShell>
  )
}
