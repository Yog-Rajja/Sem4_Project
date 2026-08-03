import { useCallback, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import Card, { CardHeader } from '../ui/Card'
import Button from '../ui/Button'
import { useToast } from '../ui/Toast'
import { SparklesIcon } from '../ui/Icons'
import cn from '../../lib/cn'
import api, { errorMessage } from '../../lib/api'

function Group({ title, items, tone }) {
  if (!items?.length) return null
  return (
    <div>
      <p className="mb-1.5 text-[11.5px] font-semibold tracking-wide text-ink-muted uppercase">
        {title}
      </p>
      <ul className="space-y-1">
        {items.map((item, index) => (
          <li
            key={index}
            className="flex gap-2 text-[13px] leading-relaxed text-ink-soft"
          >
            <span
              className={cn(
                'mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full',
                tone === 'good' && 'bg-success',
                tone === 'bad' && 'bg-warning',
                tone === 'next' && 'bg-brand-500',
              )}
            />
            {item}
          </li>
        ))}
      </ul>
    </div>
  )
}

/**
 * The week in review. Fetched on mount (cheap — it's cached server-side) and
 * only generated when the user asks, since generating costs an API call.
 */
export default function WeeklyReviewCard() {
  const toast = useToast()
  const [review, setReview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/weekly-review/')
      setReview(data.review)
    } catch {
      setReview(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  async function generate() {
    setGenerating(true)
    try {
      const { data } = await api.post('/weekly-review/', {})
      setReview(data.review)
    } catch (err) {
      toast.error(errorMessage(err, 'Could not write your review right now.'))
    } finally {
      setGenerating(false)
    }
  }

  if (loading) return null

  return (
    <Card>
      <CardHeader
        title="This week"
        subtitle={review ? review.headline : 'A short read on how the week went'}
        action={
          <Button
            variant={review ? 'ghost' : 'secondary'}
            size="sm"
            loading={generating}
            onClick={generate}
          >
            {!generating && <SparklesIcon size={14} />}
            {review ? 'Refresh' : 'Write it'}
          </Button>
        }
      />

      <div className="px-5 pb-5">
        {!review ? (
          <p className="text-[13px] leading-relaxed text-ink-muted">
            Get an honest summary of what you finished, what slipped, and what
            deserves your attention next week.
          </p>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.24 }}
            className="space-y-4"
          >
            <p className="text-[13.5px] leading-relaxed text-ink">{review.summary}</p>

            <div className="flex flex-wrap gap-x-6 gap-y-1.5 border-y border-line py-2.5 text-[12.5px] text-ink-muted">
              <span>
                <strong className="font-semibold text-ink">
                  {review.stats?.tasks_completed ?? 0}
                </strong>{' '}
                tasks done
              </span>
              <span>
                <strong className="font-semibold text-ink">
                  {review.stats?.focus_minutes ?? 0}
                </strong>{' '}
                min focused
              </span>
              <span>
                <strong className="font-semibold text-ink">
                  {review.stats?.streak ?? 0}
                </strong>
                -day streak
              </span>
            </div>

            <div className="grid gap-4 sm:grid-cols-3">
              <Group title="Wins" items={review.wins} tone="good" />
              <Group title="Slipped" items={review.slipped} tone="bad" />
              <Group title="Next week" items={review.focus_next} tone="next" />
            </div>
          </motion.div>
        )}
      </div>
    </Card>
  )
}
