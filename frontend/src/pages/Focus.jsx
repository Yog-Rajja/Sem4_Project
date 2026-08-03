import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import PageShell from '../components/layout/PageShell'
import FocusTimer from '../components/focus/FocusTimer'
import StreakCard from '../components/focus/StreakCard'
import Badge from '../components/ui/Badge'
import Card, { CardHeader } from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import { Select } from '../components/ui/Input'
import Spinner from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import { TimerIcon } from '../components/ui/Icons'
import cn from '../lib/cn'
import api, { errorMessage } from '../lib/api'
import { unwrapList } from '../lib/list'

const PRESETS = [
  { minutes: 25, mode: 'focus', label: 'Focus 25' },
  { minutes: 50, mode: 'focus', label: 'Focus 50' },
  { minutes: 5, mode: 'break', label: 'Break 5' },
  { minutes: 15, mode: 'break', label: 'Break 15' },
]

export default function Focus() {
  const toast = useToast()
  const [params] = useSearchParams()

  const [preset, setPreset] = useState(PRESETS[0])
  const [taskId, setTaskId] = useState(params.get('task') || '')
  const [tasks, setTasks] = useState([])

  const [session, setSession] = useState(null)
  const [paused, setPaused] = useState(false)
  const [busy, setBusy] = useState(false)

  const [history, setHistory] = useState([])
  const [momentum, setMomentum] = useState(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const [taskRes, sessionRes, momentumRes] = await Promise.all([
        api.get('/tasks/', { params: { status: 'pending' } }),
        api.get('/focus-sessions/'),
        api.get('/momentum/'),
      ])
      setTasks(unwrapList(taskRes.data))
      setHistory(unwrapList(sessionRes.data).filter((s) => s.ended_at))
      setMomentum(momentumRes.data)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not load your focus data.'))
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    load()
  }, [load])

  async function start() {
    setBusy(true)
    try {
      const { data } = await api.post('/focus-sessions/', {
        ...(taskId ? { task: Number(taskId) } : {}),
        mode: preset.mode,
        planned_minutes: preset.minutes,
      })
      setSession(data)
      setPaused(false)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not start that session.'))
    } finally {
      setBusy(false)
    }
  }

  const finish = useCallback(
    async (secondsElapsed, completed) => {
      if (!session) return
      setBusy(true)
      try {
        await api.post(`/focus-sessions/${session.id}/finish/`, {
          seconds_elapsed: Math.round(secondsElapsed),
          completed,
        })
        const minutes = Math.round(secondsElapsed / 60)
        toast.success(
          completed
            ? `Session complete — ${minutes} minutes banked.`
            : `Stopped early. ${minutes} minutes still counted.`,
        )
        setSession(null)
        setPaused(false)
        load()
      } catch (err) {
        toast.error(errorMessage(err, 'Could not save that session.'))
      } finally {
        setBusy(false)
      }
    },
    [session, toast, load],
  )

  const selectedTask = tasks.find((t) => String(t.id) === String(taskId))

  return (
    <PageShell
      title="Focus"
      subtitle="Work in deliberate blocks. Everything you log feeds your streak."
    >
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
        <Card className="p-6">
          {/* Preset and task pickers lock while a session is live, so a running
              timer can never silently change what it is measuring. */}
          <div className="mb-6 flex flex-wrap justify-center gap-1.5">
            {PRESETS.map((option) => (
              <button
                key={option.label}
                type="button"
                disabled={Boolean(session)}
                onClick={() => setPreset(option)}
                className={cn(
                  'rounded-full border px-3 py-1.5 text-[12.5px] font-medium transition-colors',
                  preset.label === option.label
                    ? 'border-brand-200 bg-brand-50 text-brand-700'
                    : 'border-line bg-surface text-ink-soft hover:border-line-strong',
                  session && 'opacity-50',
                )}
              >
                {option.label}
              </button>
            ))}
          </div>

          <FocusTimer
            minutes={preset.minutes}
            mode={preset.mode}
            running={Boolean(session)}
            paused={paused}
            busy={busy}
            onStart={start}
            onPause={() => setPaused(true)}
            onResume={() => setPaused(false)}
            onFinish={finish}
          />

          <div className="mt-7 border-t border-line pt-5">
            <label
              htmlFor="focus-task"
              className="mb-1.5 block text-[13px] font-medium text-ink-soft"
            >
              Working on
            </label>
            <Select
              id="focus-task"
              value={taskId}
              disabled={Boolean(session)}
              onChange={(e) => setTaskId(e.target.value)}
            >
              <option value="">Nothing specific</option>
              {tasks.map((task) => (
                <option key={task.id} value={task.id}>
                  {task.title} — {task.goal_title}
                </option>
              ))}
            </Select>
            {selectedTask && (
              <p className="mt-2 text-[12.5px] text-ink-muted">
                Part of {selectedTask.goal_title}
              </p>
            )}
          </div>
        </Card>

        <div className="space-y-3">
          <StreakCard momentum={momentum} loading={loading} />

          <Card>
            <CardHeader
              title="Recent sessions"
              subtitle={
                momentum
                  ? `${momentum.focus.total_sessions} total · ${momentum.focus.total_minutes} minutes`
                  : undefined
              }
            />
            {loading ? (
              <div className="grid place-items-center py-10 text-brand-600">
                <Spinner size={18} />
              </div>
            ) : history.length === 0 ? (
              <EmptyState
                icon={TimerIcon}
                title="No sessions yet"
                message="Start a timer and your history will build up here."
                className="py-8"
              />
            ) : (
              <ul className="px-3 pb-3">
                <AnimatePresence initial={false}>
                  {history.slice(0, 8).map((entry) => (
                    <motion.li
                      key={entry.id}
                      layout
                      initial={{ opacity: 0, y: 4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className="flex items-center gap-3 rounded-lg px-2 py-2"
                    >
                      <span
                        className={cn(
                          'grid h-7 w-7 shrink-0 place-items-center rounded-lg',
                          entry.mode === 'break'
                            ? 'bg-success-soft text-success'
                            : 'bg-brand-50 text-brand-600',
                        )}
                      >
                        <TimerIcon size={14} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-[13px] text-ink">
                          {entry.task_title || (entry.mode === 'break' ? 'Break' : 'Focus session')}
                        </span>
                        <span className="text-[12px] text-ink-muted">
                          {new Date(entry.started_at).toLocaleString(undefined, {
                            day: 'numeric',
                            month: 'short',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </span>
                      <Badge tone={entry.completed ? 'success' : 'neutral'}>
                        {entry.minutes} min
                      </Badge>
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ul>
            )}
          </Card>
        </div>
      </div>
    </PageShell>
  )
}
