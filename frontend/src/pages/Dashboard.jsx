import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
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
import WeeklyReviewCard from '../components/dashboard/WeeklyReviewCard'
import MotivationCard from '../components/dashboard/MotivationCard'
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
        <div className="flex flex-col items-center justify-center py-20 text-center bg-surface border-2 border-brand-100 rounded-3xl shadow-card">
          <motion.div
            animate={{ y: [0, -12, 0] }}
            transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
            className="text-[80px] mb-6 drop-shadow-xl select-none"
          >
            🚀
          </motion.div>
          <h2 className="font-heading text-[32px] text-ink mb-3 tracking-tight">Let's build something amazing.</h2>
          <p className="text-ink-soft mb-8 max-w-md mx-auto text-[16px] leading-relaxed font-sans">
            Describe a goal in plain English—something like "Crack GATE in 8 months"—and watch it turn into manageable milestones and daily tasks.
          </p>
          <Button size="lg" onClick={() => navigate('/goals/new')}>
            <PlusIcon size={18} />
            <span className="font-bold text-[16px]">Launch your first goal</span>
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          <MomentumStrip />

          {/* Asymmetrical 12-column editorial grid layout */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

            {/* Main Spotlight Column */}
            <div className="lg:col-span-8 flex flex-col gap-6">

              {/* Stat Tiles Layer */}
              <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
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

              {/* Primary Activity Feeds */}
              <TodayList tasks={data.today} overdue={data.overdue} onToggle={toggleTask} />

              <Card>
                <CardHeader
                  title="Goal progress & Velocity"
                  subtitle={`${goals.length} active goal${goals.length === 1 ? '' : 's'}`}
                  action={
                    <Link
                      to="/goals"
                      className="text-[13px] font-medium text-brand-600 transition-colors hover:text-brand-700 font-sans"
                    >
                      View all
                    </Link>
                  }
                />
                <div className="grid gap-3 p-4 sm:grid-cols-2">
                  {goals.map((goal, index) => (
                    <GoalProgressCard key={goal.id} goal={goal} index={index} />
                  ))}
                </div>
              </Card>
            </div>

            {/* Secondary Insight Column — Upcoming deadlines */}
            <div className="lg:col-span-4 flex flex-col gap-6">
              <DeadlineList tasks={data.upcoming} onToggle={toggleTask} />
              <MotivationCard />
            </div>

          </div>

          {/* Full-width Weekly Review — given space to breathe */}
          <WeeklyReviewCard />
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
