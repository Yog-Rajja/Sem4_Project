import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import PageShell from '../components/layout/PageShell'
import MilestoneCard from '../components/goals/MilestoneCard'
import DocumentVault from '../components/vault/DocumentVault'
import ReplanDialog from '../components/goals/ReplanDialog'
import ShareDialog from '../components/goals/ShareDialog'
import Badge from '../components/ui/Badge'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import ConfirmDialog from '../components/ui/ConfirmDialog'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import InlineEdit from '../components/ui/InlineEdit'
import ProgressBar from '../components/ui/ProgressBar'
import Spinner from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import {
  ExternalIcon,
  PlusIcon,
  TargetIcon,
  TrashIcon,
  WandIcon,
} from '../components/ui/Icons'
import api, { errorMessage } from '../lib/api'
import { formatDate } from '../lib/format'

export default function GoalDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const toast = useToast()

  const [goal, setGoal] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const [resourceState, setResourceState] = useState({}) // milestoneId -> {loading, warning}
  const [breakingDownTaskId, setBreakingDownTaskId] = useState(null)
  const [confirm, setConfirm] = useState(null) // {kind, target}
  const [confirmBusy, setConfirmBusy] = useState(false)
  const [replanOpen, setReplanOpen] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setLoadError('')
    try {
      const { data } = await api.get(`/goals/${id}/`)
      setGoal(data)
    } catch (err) {
      setLoadError(
        err?.response?.status === 404
          ? 'This goal does not exist, or is not yours.'
          : errorMessage(err, 'Could not load this goal.'),
      )
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    load()
  }, [load])

  // --- local state helpers -------------------------------------------------
  // Mutations update local state first so the UI stays responsive, then fall
  // back to a reload if the server disagrees.

  const patchMilestoneLocal = (milestoneId, patch) =>
    setGoal((current) => ({
      ...current,
      milestones: current.milestones.map((m) =>
        m.id === milestoneId ? { ...m, ...patch } : m,
      ),
    }))

  const patchTaskLocal = (taskId, patch) =>
    setGoal((current) => ({
      ...current,
      milestones: current.milestones.map((m) => ({
        ...m,
        tasks: m.tasks.map((t) => (t.id === taskId ? { ...t, ...patch } : t)),
      })),
    }))

  async function withRollback(action, message) {
    try {
      await action()
    } catch (err) {
      toast.error(errorMessage(err, message))
      load()
    }
  }

  // --- milestone actions ---------------------------------------------------

  const renameMilestone = (milestone, title) => {
    patchMilestoneLocal(milestone.id, { title })
    withRollback(
      () => api.patch(`/milestones/${milestone.id}/`, { title }),
      'Could not rename that milestone.',
    )
  }

  const changeMilestoneDate = (milestone, target_date) => {
    patchMilestoneLocal(milestone.id, { target_date })
    withRollback(
      () => api.patch(`/milestones/${milestone.id}/`, { target_date }),
      'Could not update that date.',
    )
  }

  const changeMilestoneQuery = (milestone, search_query) => {
    patchMilestoneLocal(milestone.id, { search_query })
    withRollback(
      () => api.patch(`/milestones/${milestone.id}/`, { search_query }),
      'Could not update the topic.',
    )
  }

  const toggleMilestone = (milestone) => {
    const is_complete = !milestone.is_complete
    patchMilestoneLocal(milestone.id, { is_complete })
    withRollback(
      () => api.patch(`/milestones/${milestone.id}/`, { is_complete }),
      'Could not update that milestone.',
    )
  }

  const moveMilestone = async (index, direction) => {
    const target = index + direction
    if (target < 0 || target >= goal.milestones.length) return

    const reordered = [...goal.milestones]
    ;[reordered[index], reordered[target]] = [reordered[target], reordered[index]]
    const withOrder = reordered.map((m, i) => ({ ...m, order: i }))
    setGoal((current) => ({ ...current, milestones: withOrder }))

    withRollback(
      () =>
        api.post('/milestones/reorder/', {
          items: withOrder.map((m) => ({ id: m.id, order: m.order })),
        }),
      'Could not reorder milestones.',
    )
  }

  const addMilestone = async () => {
    try {
      const { data } = await api.post('/milestones/', {
        goal: goal.id,
        title: 'New milestone',
        order: goal.milestones.length,
        search_query: '',
      })
      setGoal((current) => ({ ...current, milestones: [...current.milestones, data] }))
    } catch (err) {
      toast.error(errorMessage(err, 'Could not add a milestone.'))
    }
  }

  const fetchResources = async (milestone) => {
    setResourceState((s) => ({ ...s, [milestone.id]: { loading: true } }))
    try {
      const { data } = await api.post(`/milestones/${milestone.id}/resources/`)
      patchMilestoneLocal(milestone.id, { resources: data.resources })
      setResourceState((s) => ({
        ...s,
        [milestone.id]: { loading: false, warning: data.warning },
      }))
    } catch (err) {
      setResourceState((s) => ({ ...s, [milestone.id]: { loading: false } }))
      toast.error(errorMessage(err, 'Could not fetch resources for that milestone.'))
    }
  }

  // --- task actions --------------------------------------------------------

  const addTask = async (milestone, title) => {
    try {
      const { data } = await api.post('/tasks/', {
        milestone: milestone.id,
        title,
        order: milestone.tasks.length,
      })
      patchMilestoneLocal(milestone.id, { tasks: [...milestone.tasks, data] })
    } catch (err) {
      toast.error(errorMessage(err, 'Could not add that task.'))
    }
  }

  const taskHandlers = {
    onToggle: (task) => {
      const is_complete = !task.is_complete
      patchTaskLocal(task.id, { is_complete })
      withRollback(
        () => api.patch(`/tasks/${task.id}/`, { is_complete }),
        'Could not update that task.',
      )
    },
    onRename: (task, title) => {
      patchTaskLocal(task.id, { title })
      withRollback(
        () => api.patch(`/tasks/${task.id}/`, { title }),
        'Could not rename that task.',
      )
    },
    onDueDateChange: (task, due_date) => {
      patchTaskLocal(task.id, { due_date })
      withRollback(
        () => api.patch(`/tasks/${task.id}/`, { due_date }),
        'Could not update that due date.',
      )
    },
    onDelete: (task) => setConfirm({ kind: 'task', target: task }),
    onBreakdown: async (task) => {
      setBreakingDownTaskId(task.id)
      try {
        const { data } = await api.post(`/tasks/${task.id}/breakdown/`)
        setGoal((current) => ({
          ...current,
          milestones: current.milestones.map((m) =>
            m.id === task.milestone ? { ...m, tasks: [...m.tasks, ...data] } : m,
          ),
        }))
        toast.success(`Added ${data.length} smaller steps.`)
      } catch (err) {
        toast.error(errorMessage(err, 'Could not break that task down.'))
      } finally {
        setBreakingDownTaskId(null)
      }
    },
  }

  // --- goal actions --------------------------------------------------------

  const renameGoal = (title) => {
    setGoal((current) => ({ ...current, title }))
    withRollback(() => api.patch(`/goals/${id}/`, { title }), 'Could not rename this goal.')
  }

  const changeGoalDate = (target_date) => {
    setGoal((current) => ({ ...current, target_date }))
    withRollback(
      () => api.patch(`/goals/${id}/`, { target_date }),
      'Could not update the target date.',
    )
  }

  async function runConfirmedDelete() {
    if (!confirm) return
    setConfirmBusy(true)
    try {
      if (confirm.kind === 'goal') {
        await api.delete(`/goals/${id}/`)
        toast.success('Goal deleted.')
        navigate('/goals', { replace: true })
        return
      }
      if (confirm.kind === 'milestone') {
        await api.delete(`/milestones/${confirm.target.id}/`)
        setGoal((current) => ({
          ...current,
          milestones: current.milestones.filter((m) => m.id !== confirm.target.id),
        }))
      }
      if (confirm.kind === 'task') {
        await api.delete(`/tasks/${confirm.target.id}/`)
        setGoal((current) => ({
          ...current,
          milestones: current.milestones.map((m) => ({
            ...m,
            // Deleting a parent task cascades to its subtasks on the server.
            tasks: m.tasks.filter(
              (t) => t.id !== confirm.target.id && t.parent !== confirm.target.id,
            ),
          })),
        }))
      }
      setConfirm(null)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not delete that.'))
      load()
    } finally {
      setConfirmBusy(false)
    }
  }

  // --- derived -------------------------------------------------------------

  const stats = useMemo(() => {
    const tasks = (goal?.milestones || []).flatMap((m) => m.tasks || [])
    const done = tasks.filter((t) => t.is_complete).length
    return {
      total: tasks.length,
      done,
      progress: tasks.length ? Math.round((done * 100) / tasks.length) : 0,
    }
  }, [goal])

  if (loading) {
    return (
      <PageShell>
        <div className="grid place-items-center py-24 text-brand-600">
          <Spinner size={24} />
        </div>
      </PageShell>
    )
  }

  if (loadError) {
    return (
      <PageShell title="Goal">
        <Card>
          <ErrorState message={loadError} onRetry={load} />
          <div className="pb-6 text-center">
            <Link
              to="/goals"
              className="text-[13px] font-medium text-brand-600 hover:text-brand-700"
            >
              Back to all goals
            </Link>
          </div>
        </Card>
      </PageShell>
    )
  }

  const confirmCopy = {
    goal: {
      title: 'Delete this goal?',
      message: `“${goal.title}” and all of its milestones, tasks and resources will be permanently removed.`,
    },
    milestone: {
      title: 'Delete this milestone?',
      message: `“${confirm?.target?.title}” and its tasks will be permanently removed.`,
    },
    task: {
      title: 'Delete this task?',
      message: `“${confirm?.target?.title}” will be permanently removed.`,
    },
  }[confirm?.kind || 'task']

  return (
    <PageShell>
      <div className="mb-6">
        <Link
          to="/goals"
          className="text-[13px] font-medium text-ink-muted transition-colors hover:text-ink"
        >
          ← All goals
        </Link>

        <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <InlineEdit
              value={goal.title}
              onCommit={renameGoal}
              ariaLabel="Goal title"
              as="h1"
              className="text-xl font-semibold tracking-[-0.02em] sm:text-[22px]"
              inputClassName="text-xl font-semibold sm:text-[22px] w-full"
            />
            <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-[13px] text-ink-muted">
              <label className="flex items-center gap-1.5">
                <span>Target date</span>
                <input
                  type="date"
                  value={goal.target_date || ''}
                  onChange={(e) => changeGoalDate(e.target.value || null)}
                  aria-label="Goal target date"
                  className="rounded-md border border-line bg-surface px-1.5 py-0.5 text-[12px] outline-none focus:border-brand-500"
                />
              </label>
              {goal.target_date && (
                <span className="hidden sm:inline">· by {formatDate(goal.target_date)}</span>
              )}
              <span aria-hidden="true">·</span>
              <span>
                {goal.milestones.length} milestone
                {goal.milestones.length === 1 ? '' : 's'}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setReplanOpen(true)}>
              <WandIcon size={15} />
              Re-plan
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setShareOpen(true)}>
              <ExternalIcon size={15} />
              {goal.is_shared ? 'Shared' : 'Share'}
            </Button>
            <Button variant="secondary" size="sm" onClick={addMilestone}>
              <PlusIcon size={15} />
              Add milestone
            </Button>
            <Button
              variant="dangerGhost"
              size="icon"
              onClick={() => setConfirm({ kind: 'goal', target: goal })}
              aria-label="Delete goal"
            >
              <TrashIcon size={16} />
            </Button>
          </div>
        </div>

        <Card className="mt-4 p-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-[13px] font-medium text-ink">Overall progress</p>
              <p className="mt-0.5 text-[12.5px] text-ink-muted">
                {stats.done} of {stats.total} task{stats.total === 1 ? '' : 's'} complete
              </p>
            </div>
            <div className="flex items-center gap-3">
              {stats.progress === 100 && stats.total > 0 && (
                <Badge tone="success">Complete</Badge>
              )}
              <span className="text-lg font-semibold tabular-nums">{stats.progress}%</span>
            </div>
          </div>
          <ProgressBar value={stats.progress} className="mt-3" />
        </Card>
      </div>

      {goal.milestones.length === 0 ? (
        <Card>
          <EmptyState
            icon={TargetIcon}
            title="No milestones yet"
            message="Add a milestone to start shaping this goal into a plan you can follow."
            action={
              <Button onClick={addMilestone}>
                <PlusIcon size={15} />
                Add milestone
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          <AnimatePresence initial={false}>
            {goal.milestones.map((milestone, index) => (
              <MilestoneCard
                key={milestone.id}
                milestone={milestone}
                index={index}
                isFirst={index === 0}
                isLast={index === goal.milestones.length - 1}
                onRename={renameMilestone}
                onDateChange={changeMilestoneDate}
                onQueryChange={changeMilestoneQuery}
                onToggleComplete={toggleMilestone}
                onDelete={(m) => setConfirm({ kind: 'milestone', target: m })}
                onMove={moveMilestone}
                onAddTask={addTask}
                taskHandlers={taskHandlers}
                onFetchResources={fetchResources}
                resourcesLoading={resourceState[milestone.id]?.loading}
                resourcesWarning={resourceState[milestone.id]?.warning}
                breakingDownTaskId={breakingDownTaskId}
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      <DocumentVault goalId={goal.id} />

      <ShareDialog
        open={shareOpen}
        onClose={() => setShareOpen(false)}
        goal={goal}
        onChange={(data) =>
          setGoal((current) => ({
            ...current,
            is_shared: data.is_shared,
            share_token: data.share_token || current.share_token,
          }))
        }
      />

      <ReplanDialog
        open={replanOpen}
        onClose={() => setReplanOpen(false)}
        goal={goal}
        onReplanned={(updated) => {
          setGoal(updated)
          toast.success('Roadmap rescheduled.')
        }}
      />

      <ConfirmDialog
        open={Boolean(confirm)}
        onClose={() => !confirmBusy && setConfirm(null)}
        onConfirm={runConfirmedDelete}
        loading={confirmBusy}
        title={confirmCopy.title}
        message={confirmCopy.message}
      />
    </PageShell>
  )
}
