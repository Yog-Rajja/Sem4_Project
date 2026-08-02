import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import CompletionMeter from '../components/charts/CompletionMeter'
import GoalProgressChart from '../components/charts/GoalProgressChart'
import WorkloadChart from '../components/charts/WorkloadChart'
import Button from '../components/ui/Button'
import Card, { CardHeader } from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import Spinner from '../components/ui/Spinner'
import { ChartIcon, PlusIcon } from '../components/ui/Icons'
import api, { errorMessage } from '../lib/api'

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

  const { overall, per_goal: perGoal, workload } = data
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

  // Most-complete first, so the chart reads top-down as a ranking.
  const rankedGoals = [...perGoal]
    .filter((goal) => goal.total > 0)
    .sort((a, b) => b.progress - a.progress)

  return (
    <PageShell title="Analytics" subtitle="How your goals are tracking.">
      <div className="space-y-3">
        <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
          <Card className="p-5">
            <p className="text-[15px] font-semibold tracking-[-0.01em]">
              Overall completion
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
              title="Upcoming workload"
              subtitle="Tasks due over the next 14 days"
            />
            <div className="px-3 pb-4">
              <WorkloadChart data={workload} />
            </div>
          </Card>
        </div>

        <Card>
          <CardHeader
            title="Progress by goal"
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
