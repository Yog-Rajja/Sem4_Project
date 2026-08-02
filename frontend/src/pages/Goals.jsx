import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageShell from '../components/layout/PageShell'
import GoalCard from '../components/goals/GoalCard'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import EmptyState from '../components/ui/EmptyState'
import ErrorState from '../components/ui/ErrorState'
import Spinner from '../components/ui/Spinner'
import { PlusIcon, TargetIcon } from '../components/ui/Icons'
import api, { errorMessage } from '../lib/api'
import { unwrapList } from '../lib/list'

export default function Goals() {
  const navigate = useNavigate()
  const [goals, setGoals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.get('/goals/')
      setGoals(unwrapList(data))
    } catch (err) {
      setError(errorMessage(err, 'Could not load your goals.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  return (
    <PageShell
      title="Goals"
      subtitle={
        goals.length
          ? `${goals.length} goal${goals.length === 1 ? '' : 's'} in progress`
          : 'Everything you are working towards, in one place.'
      }
      actions={
        <Button onClick={() => navigate('/goals/new')}>
          <PlusIcon size={15} />
          New goal
        </Button>
      }
    >
      {loading ? (
        <div className="grid place-items-center py-24 text-brand-600">
          <Spinner size={24} />
        </div>
      ) : error ? (
        <Card>
          <ErrorState message={error} onRetry={load} />
        </Card>
      ) : goals.length === 0 ? (
        <Card>
          <EmptyState
            icon={TargetIcon}
            title="No goals yet"
            message="Describe something you want to achieve and we'll turn it into a dated roadmap with real learning resources."
            action={
              <Button onClick={() => navigate('/goals/new')}>
                <PlusIcon size={15} />
                Create your first goal
              </Button>
            }
          />
        </Card>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {goals.map((goal, index) => (
            <GoalCard key={goal.id} goal={goal} index={index} />
          ))}
        </div>
      )}
    </PageShell>
  )
}
