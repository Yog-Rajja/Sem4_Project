import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import CompletionMeter from '../components/charts/CompletionMeter'
import GoalProgressChart from '../components/charts/GoalProgressChart'
import WorkloadChart from '../components/charts/WorkloadChart'
import StatusPieChart from '../components/charts/StatusPieChart'
import CompletionTrendChart from '../components/charts/CompletionTrendChart'
import Button from '../components/ui/Button'
import Card, { CardHeader } from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import Spinner from '../components/ui/Spinner'
import { ChartIcon, PlusIcon } from '../components/ui/Icons'
import api, { errorMessage } from '../lib/api'
import generateReport from '../lib/generateReport'
import { useChartTheme } from '../components/charts/chartTheme'

const DownloadIcon = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
)

const FireIcon = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 12c2-2.96 0-7-1-8 0 3.038-1.773 4.741-3 6-1.226 1.26-2 3.24-2 5a6 6 0 1 0 12 0c0-1.532-1.056-3.94-2-5-1.786 3-2.791 3-4 2z" />
  </svg>
)

function StatCard({ label, value, suffix = '', color, icon, delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 24, delay }}
      className="rounded-3xl bg-surface border border-line p-5 shadow-card"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] font-semibold text-ink-muted uppercase tracking-wide">
          {label}
        </span>
        <span
          className="flex h-9 w-9 items-center justify-center rounded-xl"
          style={{ backgroundColor: `${color}20`, color }}
        >
          {icon}
        </span>
      </div>
      <div className="flex items-baseline gap-1.5">
        <span className="text-3xl font-bold tracking-[-0.03em] text-ink">
          {value}
        </span>
        {suffix && (
          <span className="text-[13px] font-semibold text-ink-muted">{suffix}</span>
        )}
      </div>
    </motion.div>
  )
}

function PieLegend({ data, theme }) {
  const total = data.reduce((s, d) => s + d.value, 0)
  return (
    <div className="flex flex-col gap-2.5 mt-4 px-2">
      {data.map((item, i) => (
        <div key={item.name} className="flex items-center justify-between text-[13px]">
          <span className="flex items-center gap-2 text-ink-soft">
            <span
              className="h-3 w-3 rounded-full"
              style={{ backgroundColor: theme.pieColors[i % theme.pieColors.length] }}
            />
            {item.name}
          </span>
          <span className="font-semibold text-ink">
            {item.value}
            <span className="text-ink-muted font-normal ml-1">
              ({total ? Math.round((item.value / total) * 100) : 0}%)
            </span>
          </span>
        </div>
      ))}
    </div>
  )
}

export default function Analytics() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await api.get('/analytics/overview/')
      setData(response.data)
    } catch (err) {
      setError(errorMessage(err, 'Could not load your analytics.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

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
      <PageShell title="Analytics">
        <Card>
          <ErrorState message={error} onRetry={load} />
        </Card>
      </PageShell>
    )
  }

  const { overall, per_goal: perGoal, workload, status_breakdown: statusBreakdown, daily_completions: dailyCompletions, streaks } = data
  const hasData = overall.total > 0

  if (!hasData) {
    return (
      <PageShell title="Analytics" subtitle="How your goals are tracking.">
        <Card>
          <EmptyState
            icon={ChartIcon}
            title="No data to chart yet"
            message="Once you have a goal with tasks, your completion rate and per-goal progress will show up here."
            action={
              <Button onClick={() => navigate('/goals/new')}>
                <PlusIcon size={15} />
                Create a goal
              </Button>
            }
          />
        </Card>
      </PageShell>
    )
  }

  const rankedGoals = [...perGoal]
    .filter((goal) => goal.total > 0)
    .sort((a, b) => b.progress - a.progress)


  return (
    <PageShell
      title="Analytics"
      subtitle="How your goals are tracking."
      actions={
        <Button variant="secondary" size="sm" onClick={() => generateReport(data)}>
          <DownloadIcon size={15} />
          Download Report
        </Button>
      }
    >
      <div className="space-y-4">
        {/* --- Hero Stat Cards --- */}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard
            label="Total Tasks"
            value={overall.total}
            color="#5AC8FA"
            icon={<ChartIcon size={18} />}
            delay={0}
          />
          <StatCard
            label="Completed"
            value={overall.completed}
            color="#61E8B2"
            icon={<ChartIcon size={18} />}
            delay={0.05}
          />
          <StatCard
            label="Completion"
            value={overall.progress}
            suffix="%"
            color="#9B6DFF"
            icon={<ChartIcon size={18} />}
            delay={0.1}
          />
          <StatCard
            label="Current Streak"
            value={streaks.current}
            suffix={streaks.current === 1 ? 'day' : 'days'}
            color="#FF6B6B"
            icon={<FireIcon size={18} />}
            delay={0.15}
          />
        </div>

        {/* --- Charts Row: Pie + Trend --- */}
        <div className="grid gap-3 lg:grid-cols-2">
          <Card className="p-5">
            <p className="text-[15px] font-semibold tracking-[-0.01em]">
              Task Status
            </p>
            <p className="mt-0.5 mb-2 text-[13px] text-ink-muted">
              Breakdown by completion state
            </p>
            <StatusPieChartWithLegend data={statusBreakdown} />
          </Card>

          <Card>
            <CardHeader
              title="Completion Trend"
              subtitle="Tasks completed per day (past 14 days)"
            />
            <div className="px-3 pb-4">
              <CompletionTrendChart data={dailyCompletions} />
            </div>
          </Card>
        </div>

        {/* --- Overall Completion + Workload --- */}
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <Card className="p-5">
            <p className="text-[15px] font-semibold tracking-[-0.01em]">
              Overall Completion
            </p>
            <p className="mt-0.5 mb-4 text-[13px] text-ink-muted">
              Across every goal and milestone
            </p>
            <CompletionMeter
              completed={overall.completed}
              pending={overall.pending}
              progress={overall.progress}
            />
          </Card>

          <Card>
            <CardHeader
              title="Upcoming Workload"
              subtitle="Tasks due over the next 14 days"
            />
            <div className="px-3 pb-4">
              <WorkloadChart data={workload} />
            </div>
          </Card>
        </div>

        {/* --- Goal Progress Bars --- */}
        <Card>
          <CardHeader
            title="Progress by Goal"
            subtitle={`${rankedGoals.length} goal${rankedGoals.length === 1 ? '' : 's'} with tasks`}
          />
          <div className="px-3 pb-4">
            {rankedGoals.length === 0 ? (
              <EmptyState
                icon={ChartIcon}
                title="No goals with tasks yet"
                message="Add tasks to a goal and its progress will chart here."
                className="py-8"
              />
            ) : (
              <GoalProgressChart data={rankedGoals} />
            )}
          </div>
        </Card>
      </div>
    </PageShell>
  )
}

function StatusPieChartWithLegend({ data }) {
  const theme = useChartTheme()

  return (
    <div>
      <StatusPieChart data={data} />
      <PieLegend data={data} theme={theme} />
    </div>
  )
}
