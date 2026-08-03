import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'
import { ErrorBanner } from '../ui/ErrorState'
import { useToast } from '../ui/Toast'
import { ClockIcon, TimerIcon, WandIcon } from '../ui/Icons'
import cn from '../../lib/cn'
import api, { errorMessage } from '../../lib/api'

const BUDGETS = [30, 60, 120, 240]

export default function PlanMyDay({ open, onClose, onTaskCompleted }) {
  const navigate = useNavigate()
  const toast = useToast()

  const [minutes, setMinutes] = useState(120)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [plan, setPlan] = useState(null)
  const [done, setDone] = useState(() => new Set())

  async function generate() {
    setLoading(true)
    setError('')
    setPlan(null)
    setDone(new Set())
    try {
      const { data } = await api.post('/plan-my-day/', { minutes })
      setPlan(data)
    } catch (err) {
      setError(errorMessage(err, 'Could not put a plan together right now.'))
    } finally {
      setLoading(false)
    }
  }

  async function complete(task) {
    try {
      await api.patch(`/tasks/${task.id}/`, { is_complete: true })
      setDone((current) => new Set(current).add(task.id))
      onTaskCompleted?.()
    } catch (err) {
      toast.error(errorMessage(err, 'Could not update that task.'))
    }
  }

  function reset() {
    setPlan(null)
    setError('')
    setDone(new Set())
    onClose()
  }

  const planned = plan?.picks.reduce((sum, p) => sum + p.estimated_minutes, 0) ?? 0

  return (
    <Modal
      open={open}
      onClose={reset}
      title="Plan my day"
      description="Tell us how long you have. We'll pick what actually fits."
      size="lg"
      footer={
        plan ? (
          <>
            <Button variant="ghost" onClick={generate} loading={loading}>
              Re-plan
            </Button>
            <Button onClick={reset}>Done</Button>
          </>
        ) : (
          <>
            <Button variant="secondary" onClick={reset}>
              Cancel
            </Button>
            <Button onClick={generate} loading={loading}>
              <WandIcon size={15} />
              Build my plan
            </Button>
          </>
        )
      }
    >
      <div className="space-y-4">
        {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

        {!plan && (
          <div>
            <p className="mb-2 text-[13px] font-medium text-ink-soft">
              How much focused time do you have?
            </p>
            <div className="flex flex-wrap gap-1.5">
              {BUDGETS.map((option) => (
                <button
                  key={option}
                  type="button"
                  disabled={loading}
                  onClick={() => setMinutes(option)}
                  className={cn(
                    'rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition-colors',
                    minutes === option
                      ? 'border-brand-200 bg-brand-50 text-brand-700'
                      : 'border-line bg-surface text-ink-soft hover:border-line-strong',
                  )}
                >
                  {option >= 60 ? `${option / 60} hr${option > 60 ? 's' : ''}` : `${option} min`}
                </button>
              ))}
            </div>
          </div>
        )}

        {loading && (
          <div className="flex items-center gap-2.5 py-6 text-[13px] text-ink-muted">
            <Spinner size={15} />
            Weighing deadlines against the time you have…
          </div>
        )}

        <AnimatePresence>
          {plan && (
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-3"
            >
              <div className="rounded-lg border border-brand-100 bg-brand-50 px-3.5 py-3">
                <p className="text-[13px] leading-relaxed text-brand-700">{plan.summary}</p>
                <p className="mt-1.5 flex items-center gap-1.5 text-[12px] text-brand-700/75">
                  <ClockIcon size={13} />
                  {planned} of your {plan.available_minutes} minutes planned
                </p>
              </div>

              <ol className="space-y-2">
                {plan.picks.map((pick, index) => {
                  const complete_ = done.has(pick.task.id)
                  return (
                    <motion.li
                      key={pick.task.id}
                      initial={{ opacity: 0, y: 6 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className={cn(
                        'flex items-start gap-3 rounded-lg border border-line bg-surface p-3',
                        complete_ && 'opacity-60',
                      )}
                    >
                      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-brand-100 text-[12px] font-semibold text-brand-700">
                        {index + 1}
                      </span>

                      <div className="min-w-0 flex-1">
                        <p
                          className={cn(
                            'text-[13.5px] font-medium text-ink',
                            complete_ && 'line-through',
                          )}
                        >
                          {pick.task.title}
                        </p>
                        <p className="mt-0.5 text-[12px] text-ink-muted">
                          {pick.task.goal_title} · {pick.reason}
                        </p>
                      </div>

                      <div className="flex shrink-0 items-center gap-1.5">
                        <span className="rounded-full border border-line px-2 py-0.5 text-[11.5px] text-ink-muted">
                          {pick.estimated_minutes}m
                        </span>
                        <button
                          type="button"
                          title="Focus on this task"
                          aria-label={`Start a focus session on ${pick.task.title}`}
                          onClick={() => {
                            reset()
                            navigate(`/focus?task=${pick.task.id}`)
                          }}
                          className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-brand-50 hover:text-brand-600"
                        >
                          <TimerIcon size={15} />
                        </button>
                        <Button
                          size="sm"
                          variant={complete_ ? 'ghost' : 'secondary'}
                          disabled={complete_}
                          onClick={() => complete(pick.task)}
                        >
                          {complete_ ? 'Done' : 'Tick off'}
                        </Button>
                      </div>
                    </motion.li>
                  )
                })}
              </ol>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </Modal>
  )
}
