import { motion } from 'framer-motion'
import cn from '../../lib/cn'

const TONES = {
  neutral: 'text-ink',
  brand: 'text-brand-600',
  warning: 'text-warning',
  danger: 'text-danger',
  success: 'text-success',
}

export default function StatTile({ label, value, tone = 'neutral', index = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, delay: index * 0.05 }}
      className="rounded-card border border-line bg-surface px-4 py-3.5 shadow-card"
    >
      <p className="text-[12px] font-medium tracking-wide text-ink-muted uppercase">
        {label}
      </p>
      <p className={cn('mt-1.5 text-2xl font-semibold tabular-nums', TONES[tone])}>
        {value}
      </p>
    </motion.div>
  )
}
