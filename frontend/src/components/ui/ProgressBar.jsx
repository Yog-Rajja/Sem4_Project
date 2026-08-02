import { motion } from 'framer-motion'
import cn from '../../lib/cn'

export default function ProgressBar({ value = 0, className, tone = 'brand' }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)))
  const complete = pct === 100

  return (
    <div
      className={cn('h-1.5 w-full overflow-hidden rounded-full bg-line', className)}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <motion.div
        className={cn(
          'h-full rounded-full',
          complete || tone === 'success' ? 'bg-success' : 'bg-brand-500',
        )}
        initial={false}
        animate={{ width: `${pct}%` }}
        transition={{ type: 'spring', stiffness: 180, damping: 26 }}
      />
    </div>
  )
}
