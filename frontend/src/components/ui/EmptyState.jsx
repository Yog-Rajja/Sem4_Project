import { motion } from 'framer-motion'
import cn from '../../lib/cn'

export default function EmptyState({ icon: Icon, title, message, action, className }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={cn('flex flex-col items-center px-6 py-12 text-center', className)}
    >
      {Icon && (
        <div className="mb-3.5 grid h-11 w-11 place-items-center rounded-xl border border-line bg-surface-muted text-ink-muted">
          <Icon size={20} />
        </div>
      )}
      <p className="text-sm font-semibold text-ink">{title}</p>
      {message && (
        <p className="mt-1.5 max-w-sm text-[13px] leading-relaxed text-ink-muted">
          {message}
        </p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </motion.div>
  )
}
