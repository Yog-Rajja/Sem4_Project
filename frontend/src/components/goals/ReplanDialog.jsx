import { useState } from 'react'
import { motion } from 'framer-motion'
import Button from '../ui/Button'
import Modal from '../ui/Modal'
import Spinner from '../ui/Spinner'
import { ErrorBanner } from '../ui/ErrorState'
import { WandIcon } from '../ui/Icons'
import api, { errorMessage } from '../../lib/api'

/**
 * Re-planning only moves dates on unfinished work — nothing is renamed,
 * deleted or un-completed — so it is safe to offer as a single button.
 */
export default function ReplanDialog({ open, onClose, goal, onReplanned }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  async function run() {
    setLoading(true)
    setError('')
    try {
      const { data } = await api.post(`/goals/${goal.id}/replan/`)
      setResult(data)
      onReplanned(data.goal)
    } catch (err) {
      setError(errorMessage(err, 'Could not re-plan this goal right now.'))
    } finally {
      setLoading(false)
    }
  }

  function close() {
    setResult(null)
    setError('')
    onClose()
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Re-plan this goal"
      description="Life happened. Rebalance what's left across the time you actually have."
      footer={
        result ? (
          <Button onClick={close}>Done</Button>
        ) : (
          <>
            <Button variant="secondary" onClick={close} disabled={loading}>
              Cancel
            </Button>
            <Button onClick={run} loading={loading}>
              <WandIcon size={15} />
              Re-plan
            </Button>
          </>
        )
      }
    >
      {error && <ErrorBanner message={error} onDismiss={() => setError('')} />}

      {loading && (
        <div className="flex items-center gap-2.5 py-4 text-[13px] text-ink-muted">
          <Spinner size={15} />
          Rebalancing the remaining milestones…
        </div>
      )}

      {!loading && !result && (
        <div className="space-y-3 text-[13.5px] leading-relaxed text-ink-soft">
          <p>
            Only the <strong className="font-medium text-ink">unfinished</strong> parts of
            “{goal.title}” will move. Completed tasks, titles and learning resources are
            left exactly as they are.
          </p>
          <ul className="space-y-1.5 text-[13px] text-ink-muted">
            <li>· Overdue work is pulled forward to today or later</li>
            <li>· Remaining milestones are spread across the time left</li>
            <li>· Nothing is pushed past your target date</li>
          </ul>
        </div>
      )}

      {result && (
        <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}>
          <div className="rounded-lg border border-brand-100 bg-brand-50 px-3.5 py-3">
            <p className="text-[13.5px] leading-relaxed text-brand-700">{result.summary}</p>
          </div>
          <p className="mt-3 text-[13px] text-ink-muted">
            Rescheduled {result.milestones_rescheduled} milestone
            {result.milestones_rescheduled === 1 ? '' : 's'} and{' '}
            {result.tasks_rescheduled} task
            {result.tasks_rescheduled === 1 ? '' : 's'}.
          </p>
        </motion.div>
      )}
    </Modal>
  )
}
