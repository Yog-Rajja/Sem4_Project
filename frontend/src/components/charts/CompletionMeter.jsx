import { motion } from 'framer-motion'
import { SERIES, SERIES_SOFT } from './chartTheme'

/**
 * Overall completion is one headline number, so it gets a hero figure and a
 * single track rather than a pie. The unfilled part is a track, not a second
 * series, and both segments are labelled directly — identity never rests on
 * colour alone.
 */
export default function CompletionMeter({ completed, pending, progress }) {
  const total = completed + pending

  return (
    <div>
      <div className="flex items-baseline gap-2.5">
        <span className="text-4xl font-semibold tracking-[-0.03em]">{progress}%</span>
        <span className="text-[13px] text-ink-muted">complete overall</span>
      </div>

      <div
        className="mt-4 flex h-3 w-full overflow-hidden rounded-full"
        style={{ backgroundColor: SERIES_SOFT }}
        role="img"
        aria-label={`${completed} of ${total} tasks complete`}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: SERIES }}
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ type: 'spring', stiffness: 150, damping: 24 }}
        />
      </div>

      <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-[12.5px]">
        <span className="flex items-center gap-1.5 text-ink-soft">
          <span
            className="h-2.5 w-2.5 rounded-[3px]"
            style={{ backgroundColor: SERIES }}
            aria-hidden="true"
          />
          {completed} completed
        </span>
        <span className="flex items-center gap-1.5 text-ink-soft">
          <span
            className="h-2.5 w-2.5 rounded-[3px]"
            style={{ backgroundColor: SERIES_SOFT }}
            aria-hidden="true"
          />
          {pending} remaining
        </span>
      </div>
    </div>
  )
}
