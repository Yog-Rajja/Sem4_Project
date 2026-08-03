import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import Badge from '../components/ui/Badge'
import Card from '../components/ui/Card'
import ProgressBar from '../components/ui/ProgressBar'
import Spinner from '../components/ui/Spinner'
import { CompassIcon, ExternalIcon } from '../components/ui/Icons'
import cn from '../lib/cn'
import api from '../lib/api'
import { formatDate } from '../lib/format'

/**
 * Read-only roadmap for anyone with the link.
 *
 * Rendered outside the authenticated shell — no sidebar, no top bar, and no
 * calls that require a token. A signed-out visitor sees the plan and nothing
 * about the person beyond a first name.
 */
export default function PublicRoadmap() {
  const { token } = useParams()
  const [goal, setGoal] = useState(null)
  const [state, setState] = useState('loading') // loading | ready | missing

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(`/public/roadmap/${token}/`)
      setGoal(data)
      setState('ready')
    } catch {
      setState('missing')
    }
  }, [token])

  useEffect(() => {
    load()
  }, [load])

  if (state === 'loading') {
    return (
      <div className="grid min-h-screen place-items-center bg-canvas text-brand-600">
        <Spinner size={26} />
      </div>
    )
  }

  if (state === 'missing') {
    return (
      <div className="grid min-h-screen place-items-center bg-canvas px-6">
        <div className="text-center">
          <h1 className="text-xl font-semibold tracking-[-0.02em] text-ink">
            This roadmap isn't available
          </h1>
          <p className="mt-2 max-w-sm text-[13.5px] text-ink-muted">
            The link may have expired, or sharing may have been turned off.
          </p>
          <Link
            to="/dashboard"
            className="mt-6 inline-flex h-9.5 items-center rounded-lg bg-brand-600 px-4 text-sm font-medium text-white transition-colors hover:bg-brand-700"
          >
            Go to Smart Companion
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-line bg-surface">
        <div className="mx-auto flex max-w-4xl items-center gap-2.5 px-4 py-3.5 sm:px-6">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-brand-600 text-white">
            <CompassIcon size={16} />
          </span>
          <span className="text-[14px] font-semibold tracking-[-0.01em]">
            Smart Companion
          </span>
          <span className="ml-auto text-[12.5px] text-ink-muted">Shared roadmap</span>
        </div>
      </header>

      <motion.main
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.24 }}
        className="mx-auto max-w-4xl px-4 py-8 sm:px-6"
      >
        <p className="text-[13px] text-ink-muted">{goal.owner_name}'s plan</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-[-0.02em] text-ink">
          {goal.title}
        </h1>

        <Card className="mt-5 p-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-[13px] font-medium text-ink">Progress</p>
              <p className="mt-0.5 text-[12.5px] text-ink-muted">
                {goal.completed_tasks} of {goal.total_tasks} tasks complete
                {goal.target_date ? ` · target ${formatDate(goal.target_date)}` : ''}
              </p>
            </div>
            <span className="text-lg font-semibold tabular-nums">{goal.progress}%</span>
          </div>
          <ProgressBar value={goal.progress} className="mt-3" />
        </Card>

        <div className="mt-4 space-y-3">
          {goal.milestones.map((milestone, index) => {
            const total = milestone.tasks.length
            const done = milestone.tasks.filter((t) => t.is_complete).length
            const videos = (milestone.resources || []).filter(
              (r) => r.source === 'youtube',
            )

            return (
              <Card key={index} className="overflow-hidden">
                <div className="flex items-start gap-3 px-4 py-3.5">
                  <span
                    className={cn(
                      'mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-md text-[12px] font-semibold',
                      milestone.is_complete
                        ? 'bg-success-soft text-success'
                        : 'bg-brand-100 text-brand-700',
                    )}
                  >
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-[14.5px] font-semibold tracking-[-0.01em] text-ink">
                        {milestone.title}
                      </h2>
                      {milestone.is_complete && <Badge tone="success">Done</Badge>}
                    </div>
                    <p className="mt-1 text-[12.5px] text-ink-muted">
                      {done}/{total} task{total === 1 ? '' : 's'}
                      {milestone.target_date
                        ? ` · by ${formatDate(milestone.target_date)}`
                        : ''}
                    </p>
                  </div>
                </div>

                <div className="border-t border-line px-4 py-2.5">
                  {milestone.tasks.map((task, taskIndex) => (
                    <div
                      key={taskIndex}
                      className="flex items-start gap-2.5 py-1.5 text-[13.5px]"
                    >
                      <span
                        className={cn(
                          'mt-1 h-3.5 w-3.5 shrink-0 rounded-[4px] border',
                          task.is_complete
                            ? 'border-success bg-success'
                            : 'border-line-strong',
                        )}
                      />
                      <span
                        className={cn(
                          'flex-1',
                          task.is_complete && 'text-ink-muted line-through',
                        )}
                      >
                        {task.title}
                      </span>
                      {task.due_date && (
                        <span className="shrink-0 text-[12px] text-ink-muted">
                          {formatDate(task.due_date)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>

                {videos.length > 0 && (
                  <div className="border-t border-line bg-surface-muted px-4 py-3">
                    <p className="mb-2 text-[11.5px] font-semibold tracking-wide text-ink-muted uppercase">
                      Learn this
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {videos.map((resource) => (
                        <a
                          key={resource.url}
                          href={resource.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-surface px-2.5 py-1.5 text-[12.5px] text-ink-soft transition-colors hover:border-brand-200 hover:text-brand-700"
                        >
                          {resource.title.slice(0, 46)}
                          {resource.title.length > 46 ? '…' : ''}
                          <ExternalIcon size={12} />
                        </a>
                      ))}
                    </div>
                  </div>
                )}
              </Card>
            )
          })}
        </div>

        <p className="mt-8 text-center text-[12.5px] text-ink-muted">
          Made with{' '}
          <Link to="/register" className="font-medium text-brand-600 hover:text-brand-700">
            Smart Companion
          </Link>
        </p>
      </motion.main>
    </div>
  )
}
