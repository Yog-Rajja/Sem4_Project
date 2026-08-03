import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import DeadlineList from '../components/dashboard/DeadlineList'
import GoalProgressCard from '../components/dashboard/GoalProgressCard'
import StatTile from '../components/dashboard/StatTile'
import TodayList from '../components/dashboard/TodayList'
import Button from '../components/ui/Button'
import Card, { CardHeader } from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import Spinner from '../components/ui/Spinner'
import { useToast } from '../components/ui/Toast'
import PlanMyDay from '../components/dashboard/PlanMyDay'
import MomentumStrip from '../components/dashboard/MomentumStrip'
import { PlusIcon, TargetIcon, WandIcon } from '../components/ui/Icons'
import { useAuth } from '../context/AuthContext'
import api, { errorMessage } from '../lib/api'

function greeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function Dashboard() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const toast = useToast()

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  // The command palette deep-links here with ?plan=1 to open the planner.
  const [planOpen, setPlanOpen] = useState(
    () => new URLSearchParams(window.location.search).get('plan') === '1',
  )

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await api.get('/dashboard/')
      setData(response.data)
    } catch (err) {
      setError(errorMessage(err, 'Could not load your dashboard.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  /** Toggling from the dashboard removes the task from these lists, so we
      update locally and refresh the counts from the server afterwards. */
  const toggleTask = async (task) => {
    const is_complete = !task.is_complete
    setData((current) => ({
      ...current,
      today: current.today.filter((t) => t.id !== task.id),
      upcoming: current.upcoming.filter((t) => t.id !== task.id),
      overdue: current.overdue.filter((t) => t.id !== task.id),
    }))
    try {
      await api.patch(`/tasks/${task.id}/`, { is_complete })
      load()
    } catch (err) {
      toast.error(errorMessage(err, 'Could not update that task.'))
      load()
    }
  }

  if (loading) {
    return (
      <PageShell>
        <div className="grid place-items-center py-24 text-brand-600">
          <Spinner size={24} />
        </div>
      </PageShell>
    )
  }

  if (error) {
    return (
      <PageShell title="Dashboard">
        <Card>
          <ErrorState message={error} onRetry={load} />
        </Card>
      </PageShell>
    )
  }

  const { stats, goals } = data
  const name = user?.first_name || user?.username || 'there'
  const hasGoals = goals.length > 0

  return (
    <PageShell
      title={`${greeting()}, ${name}`}
      subtitle={
        hasGoals
          ? 'Here is where things stand today.'
          : 'Set your first goal and we will build the plan around it.'
      }
      actions={
        <>
          {hasGoals && (
            <Button variant="secondary" onClick={() => setPlanOpen(true)}>
              <WandIcon size={15} />
              Plan my day
            </Button>
          )}
          <Button onClick={() => navigate('/goals/new')}>
            <PlusIcon size={15} />
            New goal
          </Button>
        </>
      }
    >
      {!hasGoals ? (
        <Card>
          <EmptyState
            icon={TargetIcon}
            title="Your dashboard is waiting"
            message="Describe a goal in plain English — something like “Crack GATE in 8 months” — and we'll turn it into milestones, tasks and learning resources."
            action={
              <Button size="lg" onClick={() => navigate('/goals/new')}>
                <PlusIcon size={16} />
                Create your first goal
              </Button>
            }
            className="py-16"
          />
        </Card>
      ) : (
        <div className="space-y-4">
          <MomentumStrip />

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <StatTile label="Active goals" value={stats.total_goals} index={0} />
            <StatTile label="Due today" value={stats.due_today} tone="brand" index={1} />
            <StatTile
              label="Overdue"
              value={stats.overdue}
              tone={stats.overdue > 0 ? 'danger' : 'neutral'}
              index={2}
            />
            <StatTile
              label="Completed"
              value={`${stats.completed_tasks}/${stats.total_tasks}`}
              tone="success"
              index={3}
            />
          </div>

          <div className="grid gap-3 lg:grid-cols-2">
            <TodayList tasks={data.today} overdue={data.overdue} onToggle={toggleTask} />
            <DeadlineList tasks={data.upcoming} onToggle={toggleTask} />
          </div>

          <Card>
            <CardHeader
              title="Goal progress"
              subtitle={`${goals.length} goal${goals.length === 1 ? '' : 's'}`}
              action={
                <Link
                  to="/goals"
                  className="text-[13px] font-medium text-brand-600 transition-colors hover:text-brand-700"
                >
                  View all
                </Link>
              }
            />
            <div className="grid gap-1 px-2.5 pb-3 sm:grid-cols-2 lg:grid-cols-3">
              {goals.map((goal, index) => (
                <GoalProgressCard key={goal.id} goal={goal} index={index} />
              ))}
            </div>
          </Card>
        </div>
      )}

      <PlanMyDay
        open={planOpen}
        onClose={() => setPlanOpen(false)}
        onTaskCompleted={load}
      />
    </PageShell>
  )
}
